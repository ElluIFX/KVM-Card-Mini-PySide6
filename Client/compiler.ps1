./venv/Scripts/python.exe -m nuitka  --windows-disable-console --show-progress --onefile --standalone --enable-plugin=pyside6 --include-qt-plugins=all --output-dir=build_console --windows-icon-from-ico=.\ui\images\icon.ico --jobs=16 .\ui_main.py --include-data-dir=.\ui=ui --include-data-dir=.\web=web --onefile-windows-splash-screen-image=booting.png --include-data-files=_cpyHook.cp39-win_amd64.pyd=_cpyHook.cp39-win_amd64.pyd
# --windows-disable-console  --remove-output --include-data-dir=.\ui=ui
Move-Item -Path .\build_console\ui_main.exe -Destination .\Mini-KVM-Client\Mini-KVM.exe -Force
