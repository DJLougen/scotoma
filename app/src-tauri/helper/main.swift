// scotoma-helper: the macOS-only pieces the Rust app cannot do portably.
//
//   scotoma-helper capture   interactive region screenshot → clipboard → OCR → text on stdout
//   scotoma-helper ocr       OCR the image already on the clipboard → text on stdout
//   scotoma-helper selection the text selected in the frontmost app → stdout
//   scotoma-helper record F  record the microphone to F (16 kHz mono WAV) until stdin closes
//   scotoma-helper ocr-boxes PATH   image/PDF → JSON pages of word boxes on stdout
//   scotoma-helper paint PATH OUT --boxes F [--previews DIR]
//                              same pages, each box filled black → PNG or image-only PDF
//
// Nothing leaves the machine: recognition is Apple's on-device Vision
// framework, rendering is PDFKit/CoreGraphics.
// Exit codes: 2 no image on clipboard / unreadable input, 3 no text found,
// 4 capture cancelled, 5 OCR/render error, 6 screencapture failed,
// 8 microphone unavailable, 9 nothing selected.

import AppKit
import AVFoundation
import ApplicationServices
import Quartz
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
// --- documents: OCR with word boxes, and painting them black ------------------

let PDF_DPI: CGFloat = 200

/// Render an input file to page images. PDFs rasterise at 200 dpi (each page's
/// CGSize keeps the original point size for the output PDF); images decode
/// every frame (a multi-frame TIFF becomes multiple pages).
func loadPages(_ path: String) -> [(CGImage, CGSize)] {
    let url = URL(fileURLWithPath: path)
    if url.pathExtension.lowercased() == "pdf" {
        guard let doc = PDFDocument(url: url) else { fail(2, "could not open \(path)") }
        let scale = PDF_DPI / 72.0
        var pages: [(CGImage, CGSize)] = []
        for i in 0..<doc.pageCount {
            guard let page = doc.page(at: i) else { continue }
            let rect = page.bounds(for: .mediaBox)
            let w = max(1, Int((rect.width * scale).rounded()))
            let h = max(1, Int((rect.height * scale).rounded()))
            guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8,
                                      bytesPerRow: 0,
                                      space: CGColorSpaceCreateDeviceRGB(),
                                      bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGImageByteOrderInfo.order32Little.rawValue) else {
                fail(5, "could not create a render context")
            }
            ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
            ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
            ctx.saveGState()
            ctx.scaleBy(x: scale, y: scale)
            page.draw(with: .mediaBox, to: ctx)
            ctx.restoreGState()
            guard let img = ctx.makeImage() else { fail(5, "could not render page \(i + 1)") }
            pages.append((img, rect.size))
        }
        if pages.isEmpty { fail(2, "\(path) has no pages") }
        return pages
    }
    // Image input: every bitmap frame is a page.
    guard let data = FileManager.default.contents(atPath: path) else { fail(2, "could not read \(path)") }
    var pages: [(CGImage, CGSize)] = []
    for rep in (NSBitmapImageRep.imageReps(with: data) as? [NSBitmapImageRep]) ?? [] {
        if let cg = rep.cgImage {
            pages.append((cg, CGSize(width: cg.width, height: cg.height)))
        }
    }
    if pages.isEmpty, let img = NSImage(contentsOfFile: path) {
        var r = CGRect(origin: .zero, size: img.size)
        if let cg = img.cgImage(forProposedRect: &r, context: nil, hints: nil) {
            pages.append((cg, r.size))
        }
    }
    if pages.isEmpty { fail(2, "could not decode \(path) as an image") }
    return pages
}

/// OCR one page image into JSON: lines in reading order, words with character
/// offsets into the line text and pixel boxes (top-left origin). Vision boxes
/// are normalised, bottom-left origin.
func ocrBoxesJson(_ image: CGImage) -> [String: Any] {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = false   // identifiers must come through verbatim
    let handler = VNImageRequestHandler(cgImage: image, options: [:])
    do { try handler.perform([request]) } catch { fail(5, "text recognition failed: \(error.localizedDescription)") }

    let w = Double(image.width), h = Double(image.height)
    var lines: [[String: Any]] = []
    for obs in request.results ?? [] {
        guard let cand = obs.topCandidates(1).first else { continue }
        let lineText = cand.string
        let lb = obs.boundingBox
        var words: [[String: Any]] = []
        var idx = lineText.startIndex
        while idx < lineText.endIndex {
            while idx < lineText.endIndex && lineText[idx].isWhitespace { idx = lineText.index(after: idx) }
            if idx >= lineText.endIndex { break }
            let start = idx
            while idx < lineText.endIndex && !lineText[idx].isWhitespace { idx = lineText.index(after: idx) }
            let range = start..<idx
            let word = String(lineText[range])
            let cs = lineText.distance(from: lineText.startIndex, to: start)
            let ce = lineText.distance(from: lineText.startIndex, to: idx)
            var wb: CGRect?
            if let o = try? cand.boundingBox(for: range) { wb = o.boundingBox }
            if wb == nil {
                // No per-word box: slice the line's box proportionally so the
                // redaction still covers the word.
                let total = max(1, lineText.count)
                let x0 = lb.minX + lb.width * CGFloat(cs) / CGFloat(total)
                let x1 = lb.minX + lb.width * CGFloat(ce) / CGFloat(total)
                wb = CGRect(x: x0, y: lb.minY, width: max(0.001, x1 - x0), height: lb.height)
            }
            let b = wb!
            // normalised bottom-left → pixel top-left
            words.append([
                "text": word, "start": cs, "end": ce,
                "box": [b.minX * w, (1 - b.maxY) * h, b.width * w, b.height * h],
            ])
        }
        lines.append(["text": lineText, "words": words])
    }
    return ["width": image.width, "height": image.height, "lines": lines]
}

func ocrBoxes(_ path: String) -> Never {
    let pages = loadPages(path)
    let out: [String: Any] = ["pages": pages.map { ocrBoxesJson($0.0) }]
    guard let data = try? JSONSerialization.data(withJSONObject: out, options: [.sortedKeys]) else {
        fail(5, "could not encode OCR results")
    }
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write("\n".data(using: .utf8)!)
    exit(0)
}

/// Fill `rects` (pixel coords, top-left origin) solid black on top of a page
/// image inside a y-up CoreGraphics context whose user space is the page size.
func paintBoxes(_ ctx: CGContext, pageSize: CGSize, _ rects: [CGRect]) {
    guard !rects.isEmpty else { return }
    ctx.saveGState()
    ctx.translateBy(x: 0, y: pageSize.height)
    ctx.scaleBy(x: 1, y: -1)   // now drawing in top-left-origin coordinates
    ctx.setFillColor(CGColor(red: 0, green: 0, blue: 0, alpha: 1))
    for r in rects { ctx.fill(r) }
    ctx.restoreGState()
}

/// The pixel boxes for each page, parsed from --boxes JSON.
func readBoxes(_ path: String) -> [[CGRect]] {
    struct Entry: Decodable { let page: Int; let box: [Double] }
    struct Job: Decodable { let boxes: [Entry] }
    guard let data = FileManager.default.contents(atPath: path),
          let job = try? JSONDecoder().decode(Job.self, from: data) else {
        fail(2, "could not read boxes file \(path)")
    }
    var byPage: [[CGRect]] = []
    for e in job.boxes where e.box.count == 4 {
        while byPage.count <= e.page { byPage.append([]) }
        byPage[e.page].append(CGRect(x: e.box[0], y: e.box[1], width: e.box[2], height: e.box[3]))
    }
    return byPage
}

/// Rasterise the input (never drawing into the original PDF), paint every box
/// black, and write OUT: PNG for a single-page image, a fresh image-only PDF
/// (no text layer, no annotations, no metadata) otherwise. --previews DIR also
/// writes DIR/page-N.png so a caller can show the result without re-rendering.
func paint(_ input: String, _ out: String, _ boxesPath: String, _ previewsDir: String?) -> Never {
    let pages = loadPages(input)
    let boxes = readBoxes(boxesPath)
    let isPDFInput = input.lowercased().hasSuffix(".pdf")
    var painted: [(CGImage, CGSize)] = []
    for (i, (img, size)) in pages.enumerated() {
        let rects = i < boxes.count ? boxes[i] : []
        guard let ctx = CGContext(data: nil, width: img.width, height: img.height,
                                  bitsPerComponent: 8, bytesPerRow: 0,
                                  space: CGColorSpaceCreateDeviceRGB(),
                                  bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGImageByteOrderInfo.order32Little.rawValue) else {
            fail(5, "could not create a paint context")
        }
        ctx.draw(img, in: CGRect(x: 0, y: 0, width: img.width, height: img.height))
        paintBoxes(ctx, pageSize: CGSize(width: img.width, height: img.height), rects)
        guard let done = ctx.makeImage() else { fail(5, "could not produce page \(i + 1)") }
        painted.append((done, size))
        if let dir = previewsDir {
            try? FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
            let rep = NSBitmapImageRep(cgImage: done)
            if let png = rep.representation(using: .png, properties: [:]) {
                try? png.write(to: URL(fileURLWithPath: dir).appendingPathComponent("page-\(i + 1).png"))
            }
        }
    }
/// Byte-search helper for stripPdfInfo.
func indexOf(_ needle: [UInt8], in hay: [UInt8], from: Int, last: Bool) -> Int? {
    guard needle.count <= hay.count else { return nil }
    var hit: Int? = nil
    var i = max(0, from)
    while i + needle.count <= hay.count {
        if Array(hay[i..<i + needle.count]) == needle {
            if !last { return i }
            hit = i; i += needle.count
        } else { i += 1 }
    }
    return hit
}

/// Quartz always stamps Producer/CreationDate/ModDate into the PDF's Info
/// dictionary and there is no API to stop it, so after writing we find the
/// Info object the trailer points at and blank its dictionary in place,
/// padding with spaces to keep every byte offset (and the xref) valid.
func stripPdfInfo(_ path: String) {
    let url = URL(fileURLWithPath: path)
    guard let data = try? Data(contentsOf: url) else { return }
    var bytes = [UInt8](data)
    // trailer's "/Info <obj> <gen> R" is the last /Info in the file
    guard let t = indexOf([UInt8]("/Info".utf8), in: bytes, from: 0, last: true) else { return }
    var i = t + 5
    while i < bytes.count && bytes[i] == 32 { i += 1 }
    var objNum = 0
    while i < bytes.count && bytes[i] >= 48 && bytes[i] <= 57 {
        objNum = objNum * 10 + Int(bytes[i] - 48); i += 1
    }
    guard objNum > 0 else { return }
    guard let m = indexOf([UInt8]("\(objNum) 0 obj".utf8), in: bytes, from: 0, last: true) else { return }
    guard let open = indexOf([UInt8]("<<".utf8), in: bytes, from: m, last: false),
          let close = indexOf([UInt8](">>".utf8), in: bytes, from: open + 2, last: false) else { return }
    for j in (open + 2)..<close { bytes[j] = 32 }
    try? Data(bytes).write(to: url)
}

    if painted.count == 1 && !isPDFInput {
        // Fresh PNG re-encode: no EXIF or other metadata from the input survives.
        let rep = NSBitmapImageRep(cgImage: painted[0].0)
        guard let png = rep.representation(using: .png, properties: [:]) else {
            fail(5, "could not encode PNG")
        }
        do { try png.write(to: URL(fileURLWithPath: out)) } catch { fail(5, "could not write \(out)") }
    } else {
        // A brand-new PDFDocument built only from painted images: no pages,
        // annotations, or metadata from the source survive.
        let doc = PDFDocument()
        for (img, size) in painted {
            let ns = NSImage(cgImage: img, size: size)
            guard let page = PDFPage(image: ns) else { fail(5, "could not build a PDF page") }
            page.setBounds(CGRect(origin: .zero, size: size), for: .mediaBox)
            doc.insert(page, at: doc.pageCount)
        }
        if !doc.write(toFile: out) { fail(5, "could not write \(out)") }
        // Quartz stamps Producer/dates into the Info dict; blank them out.
        stripPdfInfo(out)
    }
    print("{\"pages\": \(painted.count)}")
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
case "ocr-boxes":
    guard CommandLine.arguments.count > 2 else { fail(64, "ocr-boxes needs a file path") }
    ocrBoxes(CommandLine.arguments[2])
case "paint":
    // paint IN OUT --boxes BOXES.json [--previews DIR]
    let args = Array(CommandLine.arguments.dropFirst(2))
    guard args.count >= 4, args[2] == "--boxes" else {
        fail(64, "usage: scotoma-helper paint IN OUT --boxes BOXES.json [--previews DIR]")
    }
    var previews: String? = nil
    var rest = args.dropFirst(4)
    while let flag = rest.first {
        rest = rest.dropFirst()
        switch flag {
        case "--previews":
            guard let d = rest.first else { fail(64, "--previews needs a directory") }
            previews = d; rest = rest.dropFirst()
        default: fail(64, "unknown paint option \(flag)")
        }
    }
    paint(args[0], args[1], args[3], previews)
default: fail(64, "usage: scotoma-helper capture | ocr | selection | record FILE | ocr-boxes FILE | paint IN OUT --boxes F [--previews DIR]")
}
