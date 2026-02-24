# mxctl demo recording
# Run: vhs demo/demo.tape

Output demo/demo.gif
Set Shell "bash"
Set FontSize 15
Set Width 900
Set Height 550
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms
Set CursorBlink false

Sleep 500ms

# Show version
Type "mxctl --version"
Enter
Sleep 1.5s

# Check inbox
Type "mxctl inbox"
Enter
Sleep 3s

# Triage unread
Type "mxctl triage"
Enter
Sleep 4s

# AI summary
Type "mxctl summary"
Enter
Sleep 4s

# Batch-read newsletters
Type "mxctl batch-read --unread -m INBOX"
Enter
Sleep 2.5s

Sleep 2s
