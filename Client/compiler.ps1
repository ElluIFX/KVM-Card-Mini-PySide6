nuitka  --windows-disable-console --show-progress --onefile --standalone --enable-plugin=pyqt5 --include-qt-plugins=all --output-dir=build_console --windows-icon-from-ico=.\ui\images\icon.ico --jobs 16 .\main.py --include-data-dir=.\ui=ui
# --windows-disable-console  --remove-output --include-data-dir=.\ui=ui
Move-Item -Path .\build_console\main.exe -Destination .\Mini-KVM-Client\Mini-KVM.exe -Force
