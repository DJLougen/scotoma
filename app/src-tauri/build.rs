use std::path::Path;
use std::process::Command;

fn main() {
    println!("cargo:rerun-if-changed=helper/main.swift");
    let manifest = std::env::var("CARGO_MANIFEST_DIR").unwrap_or_default();
    let helper = Path::new(&manifest).join("bin").join("scotoma-helper");
    println!("cargo:rustc-env=SCOTOMA_HELPER_DEV={}", helper.display());

    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("macos") {
        let src = Path::new(&manifest).join("helper").join("main.swift");
        let stale = match (std::fs::metadata(&helper).and_then(|m| m.modified()), std::fs::metadata(&src).and_then(|m| m.modified())) {
            (Ok(h), Ok(s)) => h < s,
            _ => true,
        };
        if stale {
            let ok = Command::new("swiftc").arg("-O").arg(&src).arg("-o").arg(&helper).status().map(|s| s.success()).unwrap_or(false);
            if !ok {
                println!("cargo:warning=could not build the screen-capture helper (needs Xcode command line tools); screen capture will be unavailable");
            }
        }
    }
    tauri_build::build()
}
