!macro NSIS_HOOK_POSTUNINSTALL
  ; Remove downloaded whisper models on uninstall (current user scope)
  RMDir /r "$APPDATA\\com.example.whisper-desktop\\models"
!macroend
