// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

/// Проверяет, не запущен ли уже экземпляр приложения, через именованный мьютекс.
/// Если да — завершает процесс без показа окна.
#[cfg(windows)]
fn enforce_single_instance() {
    use std::ffi::OsStr;
    use std::os::windows::ffi::OsStrExt;

    #[link(name = "kernel32")]
    extern "system" {
        fn CreateMutexW(
            lpMutexAttributes: *const std::ffi::c_void,
            bInitialOwner: i32,
            lpName: *const u16,
        ) -> isize;
        fn GetLastError() -> u32;
        fn SetLastError(dwErrCode: u32);
    }

    let name: Vec<u16> = OsStr::new("AIOS-Desktop-Single-Instance")
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();

    const ERROR_ALREADY_EXISTS: u32 = 183;

    unsafe {
        SetLastError(0);
        let handle = CreateMutexW(std::ptr::null(), 0, name.as_ptr());
        if handle == 0 {
            return;
        }
        if GetLastError() == ERROR_ALREADY_EXISTS {
            std::process::exit(0);
        }
    }
}

#[cfg(not(windows))]
fn enforce_single_instance() {}

fn main() {
    enforce_single_instance();
    aios_desktop::run();
}
