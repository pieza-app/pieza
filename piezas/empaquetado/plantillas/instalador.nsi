; Instalador de {{nombre}} para Windows (por usuario, sin permisos de administrador).
; Lo arma herramientas/instalador-windows.sh con makensis (corre en Linux/Mac, sin Wine).
; Con /S instala en silencio y abre {{nombre}} al terminar (lo usan instalar.ps1 y el actualizador de la app).
; Generado por la pieza «empaquetado» de Pieza (MPL-2.0, https://mozilla.org/MPL/2.0/) desde app.json.
Unicode true
SetCompressor /SOLID lzma
RequestExecutionLevel user
!include "MUI2.nsh"

Name "{{nombre}}"
OutFile "${SALIDA}"
InstallDir "$LOCALAPPDATA\Programs\{{nombre_ascii}}"
BrandingText "{{nombre}} ${VERSION}"
VIProductVersion "${VERSION}.0"
VIAddVersionKey /LANG=0 "ProductName" "{{nombre}}"
VIAddVersionKey /LANG=0 "FileDescription" "Instalador de {{nombre}}"
VIAddVersionKey /LANG=0 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=0 "ProductVersion" "${VERSION}"
VIAddVersionKey /LANG=0 "LegalCopyright" "{{#si app.empaquetado.licencia}}{{app.empaquetado.licencia|nombre}}{{#sino}}AGPL-3.0{{/si}}"

!define MUI_ICON "${ICONO}"
!define MUI_UNICON "${ICONO}"
!define MUI_FINISHPAGE_RUN "$INSTDIR\{{nombre_ascii}}.exe"
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Spanish"
!insertmacro MUI_LANGUAGE "English"

!define DESINSTALAR "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{nombre_ascii}}"

Section "{{nombre}}"
  ; Si está abierta (p. ej. al actualizar) se le pide cerrar (guarda lo pendiente) y, si no alcanza, se cierra para poder
  ; reemplazar sus archivos.
  nsExec::Exec 'taskkill /IM {{nombre_ascii}}.exe'
  Sleep 2500
  nsExec::Exec 'taskkill /IM {{nombre_ascii}}.exe /F'
  Sleep 500
  RMDir /r "$INSTDIR"
  SetOutPath "$INSTDIR"
  File /r "${ORIGEN}\*.*"
  WriteUninstaller "$INSTDIR\Desinstalar {{nombre_ascii}}.exe"
  CreateShortcut "$SMPROGRAMS\{{nombre}}.lnk" "$INSTDIR\{{nombre_ascii}}.exe"
  CreateShortcut "$DESKTOP\{{nombre}}.lnk" "$INSTDIR\{{nombre_ascii}}.exe"
  WriteRegStr HKCU "${DESINSTALAR}" "DisplayName" "{{nombre}}"
  WriteRegStr HKCU "${DESINSTALAR}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${DESINSTALAR}" "Publisher" "{{nombre}} (open source)"
  WriteRegStr HKCU "${DESINSTALAR}" "DisplayIcon" "$INSTDIR\{{nombre_ascii}}.exe"
  WriteRegStr HKCU "${DESINSTALAR}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${DESINSTALAR}" "UninstallString" '"$INSTDIR\Desinstalar {{nombre_ascii}}.exe"'
  WriteRegStr HKCU "${DESINSTALAR}" "QuietUninstallString" '"$INSTDIR\Desinstalar {{nombre_ascii}}.exe" /S'
  WriteRegStr HKCU "${DESINSTALAR}" "URLInfoAbout" "{{web}}"
  WriteRegDWORD HKCU "${DESINSTALAR}" "NoModify" 1
  WriteRegDWORD HKCU "${DESINSTALAR}" "NoRepair" 1
  IfSilent 0 +2
    Exec '"$INSTDIR\{{nombre_ascii}}.exe"'
SectionEnd

; Desinstalar quita la app; tus datos no se tocan.
Section "Uninstall"
  nsExec::Exec 'taskkill /IM {{nombre_ascii}}.exe /F'
  Sleep 800
  Delete "$SMPROGRAMS\{{nombre}}.lnk"
  Delete "$DESKTOP\{{nombre}}.lnk"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKCU "${DESINSTALAR}"
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "{{bundle_escritorio}}"
SectionEnd
