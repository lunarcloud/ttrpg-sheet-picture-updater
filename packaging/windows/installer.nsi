; NSIS script for the Windows installer, replacing the earlier .msix
; approach (see packaging/README.md's Windows section for the rationale:
; MSIX requires end users to manually import/trust a self-signed
; certificate before Windows allows installation at all, which was
; confusing and error-prone — an unsigned NSIS .exe only triggers a
; dismissable SmartScreen "unknown publisher" prompt, no certificate
; import required).
;
; Built by packaging/build-nsis.sh via makensis, with these values passed
; in as /D command-line defines (never hand-edit them here):
;   VERSION          e.g. "1.2.3" or "2.0.0-alpha.6" (from
;                    .VERSION-PLACEHOLDER) — used for display purposes
;                    (DisplayVersion, ProductVersion, FileVersion keys).
;   VERSION_NUMERIC  a strict X.X.X.X numeric version derived from
;                    VERSION (prerelease/build suffixes stripped, padded
;                    to 4 components) — VIProductVersion requires this
;                    exact format and rejects suffixes like "-alpha.6".
;   STAGE_DIR        absolute path to the PyInstaller one-dir build to
;                    bundle (dist/set-ttrpg-portrait-launcher/, see
;                    set-ttrpg-portrait-windows.spec)
;   ICON_FILE        absolute path to packaging/windows/icon.ico
;   OUT_FILE         absolute path the finished installer .exe is written to
;
; Installs per-user (no admin/UAC elevation needed) to
; %LOCALAPPDATA%\Programs\set-ttrpg-portrait, matching the same
; "no elevation, no cert, no fuss" philosophy as the AppImage on Linux.

!include "MUI2.nsh"

; Friendly display name shown in the installer UI, Start Menu, and
; Add/Remove Programs — kept separate from the kebab-case install
; dir/registry key names below (changing those would complicate
; upgrade/uninstall lookups for existing installs).
!define APP_NAME "Set TTRPG Portrait"

Name "${APP_NAME}"
OutFile "${OUT_FILE}"
Unicode True
InstallDir "$LOCALAPPDATA\Programs\set-ttrpg-portrait"
InstallDirRegKey HKCU "Software\set-ttrpg-portrait" "InstallDir"
RequestExecutionLevel user
Icon "${ICON_FILE}"
UninstallIcon "${ICON_FILE}"
VIProductVersion "${VERSION_NUMERIC}"
VIAddVersionKey "ProductName" "${APP_NAME}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "FileDescription" "Embed a portrait image into a fillable TTRPG character sheet PDF"
VIAddVersionKey "LegalCopyright" "lunarcloud"

!define MUI_ABORTWARNING
!define MUI_ICON "${ICON_FILE}"
!define MUI_UNICON "${ICON_FILE}"
!define MUI_FINISHPAGE_RUN "$INSTDIR\set-ttrpg-portrait-launcher.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APP_NAME}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

!define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\set-ttrpg-portrait"

Section "Install" SEC_INSTALL
    SetOutPath "$INSTDIR"
    File /r "${STAGE_DIR}\*.*"

    WriteRegStr HKCU "Software\set-ttrpg-portrait" "InstallDir" "$INSTDIR"
    WriteUninstaller "$INSTDIR\uninstall.exe"

    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
        "$INSTDIR\set-ttrpg-portrait-launcher.exe" "" "$INSTDIR\set-ttrpg-portrait-launcher.exe"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\uninstall.exe"

    ; HKCU (not HKLM) so this matches the per-user, no-elevation install.
    WriteRegStr HKCU "${UNINST_KEY}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKCU "${UNINST_KEY}" "DisplayVersion" "${VERSION}"
    WriteRegStr HKCU "${UNINST_KEY}" "Publisher" "lunarcloud"
    WriteRegStr HKCU "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "${UNINST_KEY}" "DisplayIcon" "$INSTDIR\set-ttrpg-portrait-launcher.exe"
    WriteRegStr HKCU "${UNINST_KEY}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegDWORD HKCU "${UNINST_KEY}" "NoModify" 1
    WriteRegDWORD HKCU "${UNINST_KEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
    RMDir /r "$INSTDIR"
    RMDir /r "$SMPROGRAMS\${APP_NAME}"
    DeleteRegKey HKCU "${UNINST_KEY}"
    DeleteRegKey HKCU "Software\set-ttrpg-portrait"
SectionEnd
