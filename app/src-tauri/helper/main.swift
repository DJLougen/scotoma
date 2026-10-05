// scotoma-helper: the macOS-only pieces the Rust app cannot do portably.
//
//   scotoma-helper capture   interactive region screenshot → clipboard → OCR → text on stdout
//   scotoma-helper ocr       OCR the image already on the clipboard → text on stdout
//   scotoma-helper selection the text selected in the frontmost app → stdout
//   scotoma-helper record F  record the microphone to F (16 kHz mono WAV) until stdin closes
//
// Nothing is written to disk and nothing leaves the machine: the screenshot goes
// to the clipboard, recognition is Apple's on-device Vision framework.
// Exit codes: 2 no image on clipboard, 3 no text found, 4 capture cancelled,
// 5 OCR error, 6 screencapture failed, 8 microphone unavailable, 9 nothing selected.

import AppKit
import AVFoundation
import ApplicationServices
import Vision

func fail(_ code: Int32, _ msg: String) -> Never {
    FileHandle.standardError.write((msg + "\n").data(using: .utf8)!)
    exit(code)
}

func pasteboardImage() -> CGImage? {
    let pb = NSPasteboard.general
    // Prefer the raw bitmap so a Retina screenshot keeps its full resolution.
    for type in [NSPasteboard.PasteboardType.png, NSPasteboard.PasteboardType.tiff] {
        if let data = pb.data(forType: type), let rep = NSBitmapImageRep(data: data), let cg = rep.cgImage {
            return cg
        }
    }
    if let img = NSImage(pasteboard: pb) {
        var rect = CGRect(origin: .zero, size: img.size)
        return img.cgImage(forProposedRect: &rect, context: nil, hints: nil)
    }
    return nil
}

func recognise(_ image: CGImage) -> String {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    // Language correction "fixes" record numbers and surnames into dictionary
    // words. Identifiers must come through verbatim, so it stays off.
    request.usesLanguageCorrection = false
    let handler = VNImageRequestHandler(cgImage: image, options: [:])
    do { try handler.perform([request]) } catch { fail(5, "text recognition failed: \(error.localizedDescription)") }

    struct Piece { let text: String; let box: CGRect }
    var pieces: [Piece] = []
    for obs in request.results ?? [] {
        if let best = obs.topCandidates(1).first { pieces.append(Piece(text: best.string, box: obs.boundingBox)) }
    }
    // Vision's boxes are normalised with the origin at the bottom-left.
    // Rebuild reading order: top to bottom, then left to right within a row.
    pieces.sort { $0.box.midY > $1.box.midY }
    var rows: [[Piece]] = []
    for p in pieces {
        if let last = rows.last, let ref = last.first, abs(ref.box.midY - p.box.midY) < min(ref.box.height, p.box.height) * 0.6 {
            rows[rows.count - 1].append(p)
        } else {
            rows.append([p])
        }
    }
    return rows.map { row in row.sorted { $0.box.minX < $1.box.minX }.map { $0.text }.joined(separator: "   ") }
        .joined(separator: "\n")
}

func ocrClipboard() -> Never {
    guard let image = pasteboardImage() else { fail(2, "no image on the clipboard") }
    let text = recognise(image)
    if text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { fail(3, "no text found in the image") }
    print(text)
    exit(0)
}

// screencapture -i takes the next mouse/keyboard events as part of the
// selection. Started while the hotkey's modifiers are still held, or while the
// mouse button that clicked "Capture" is still down, it sees those releases
// and cancels at once. So wait until the user has let go of everything.
func waitForInputIdle() {
    let mods: CGEventFlags = [.maskCommand, .maskAlternate, .maskControl, .maskShift]
    let deadline = Date().addingTimeInterval(4)
    while Date() < deadline {
        let held = !CGEventSource.flagsState(.combinedSessionState).intersection(mods).isEmpty
            || CGEventSource.buttonState(.combinedSessionState, button: .left)
            || CGEventSource.buttonState(.combinedSessionState, button: .right)
        if !held { break }
        usleep(15_000)
    }
    usleep(120_000)   // let the release events drain before the overlay appears
}

func capture() -> Never {
    waitForInputIdle()
    let pb = NSPasteboard.general
    let before = pb.changeCount
    let p = Process()
    p.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
    p.arguments = ["-i", "-c", "-x"]   // interactive region, to clipboard, no sound
    do { try p.run() } catch { fail(6, "could not start screencapture") }
    p.waitUntilExit()
    if pb.changeCount == before { exit(4) }   // Esc pressed
    ocrClipboard()
}

// --- selected text -------------------------------------------------------------
// First ask the focused control directly (Accessibility). If the app does not
// expose its selection, press ⌘C for the user, read the result, and put the
// clipboard back the way it was so the unredacted text does not linger there.
func selection() -> Never {
    let trusted = AXIsProcessTrustedWithOptions(["AXTrustedCheckOptionPrompt": true] as CFDictionary)
    if trusted {
        let system = AXUIElementCreateSystemWide()
        var focused: CFTypeRef?
        if AXUIElementCopyAttributeValue(system, kAXFocusedUIElementAttribute as CFString, &focused) == .success,
           let element = focused, CFGetTypeID(element) == AXUIElementGetTypeID() {
            var value: CFTypeRef?
            if AXUIElementCopyAttributeValue(element as! AXUIElement, kAXSelectedTextAttribute as CFString, &value) == .success,
               let text = value as? String, !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                print(text)
                exit(0)
            }
        }
    }

    let pb = NSPasteboard.general
    let before = pb.changeCount
    // Snapshot everything on the clipboard (text, images, files) to restore it.
    var saved: [[(NSPasteboard.PasteboardType, Data)]] = []
    for item in pb.pasteboardItems ?? [] {
        saved.append(item.types.compactMap { t in item.data(forType: t).map { (t, $0) } })
    }
    usleep(150_000)   // let the hotkey's own modifiers come up
    let source = CGEventSource(stateID: .combinedSessionState)
    let keyC: CGKeyCode = 8
    for down in [true, false] {
        let ev = CGEvent(keyboardEventSource: source, virtualKey: keyC, keyDown: down)
        ev?.flags = .maskCommand
        ev?.post(tap: .cghidEventTap)
    }
    var waited = 0
    while pb.changeCount == before && waited < 60 { usleep(10_000); waited += 1 }
    if pb.changeCount == before { exit(9) }
    let text = pb.string(forType: .string) ?? ""
    pb.clearContents()
    let items: [NSPasteboardItem] = saved.map { entries in
        let item = NSPasteboardItem()
        for (t, d) in entries { item.setData(d, forType: t) }
        return item
    }
    if !items.isEmpty { pb.writeObjects(items) }
    if text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { exit(9) }
    print(text)
    exit(0)
}

// --- microphone ----------------------------------------------------------------
func record(_ path: String) -> Never {
    let gate = DispatchSemaphore(value: 0)
    var allowed = false
    AVCaptureDevice.requestAccess(for: .audio) { ok in allowed = ok; gate.signal() }
    gate.wait()
    if !allowed { fail(8, "microphone access was denied") }
    let settings: [String: Any] = [
        AVFormatIDKey: kAudioFormatLinearPCM, AVSampleRateKey: 16000.0, AVNumberOfChannelsKey: 1,
        AVLinearPCMBitDepthKey: 16, AVLinearPCMIsFloatKey: false, AVLinearPCMIsBigEndianKey: false,
    ]
    guard let recorder = try? AVAudioRecorder(url: URL(fileURLWithPath: path), settings: settings), recorder.record() else {
        fail(8, "could not start recording")
    }
    print("RECORDING")
    _ = readLine()        // returns when the app writes a line or closes the pipe
    recorder.stop()
    exit(0)
}

switch CommandLine.arguments.dropFirst().first {
case "capture": capture()
case "ocr": ocrClipboard()
case "selection": selection()
case "record":
    guard CommandLine.arguments.count > 2 else { fail(64, "record needs a file path") }
    setvbuf(stdout, nil, _IOLBF, 0)
    record(CommandLine.arguments[2])
default: fail(64, "usage: scotoma-helper capture | ocr | selection | record FILE")
}
