#!/bin/bash
# Build script for CH582F KVM firmware
# Toolchain: MounRiver Studio 2 RISC-V Embedded GCC 8.2.0
# Settings derived from MRS2 .cproject (CH582F template)

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
TOOLCHAIN="/c/MounRiver/MounRiver_Studio/MounRiver_Studio2/resources/app/resources/win32/components/WCH/Toolchain/RISC-V Embedded GCC"
CC="${TOOLCHAIN}/bin/riscv-none-embed-gcc.exe"
OBJCOPY="${TOOLCHAIN}/bin/riscv-none-embed-objcopy.exe"
SIZE="${TOOLCHAIN}/bin/riscv-none-embed-size.exe"

BUILD_DIR="${PROJECT_ROOT}/build"
mkdir -p "${BUILD_DIR}"

# ==========================================================================
# Compiler flags (from MRS2 .cproject for CH582F)
# ==========================================================================
# Architecture: rv32imac (base rv32i + M multiply + A atomic + C compressed)
# ABI: ilp32 (no hardware float)
ARCH_FLAGS="-march=rv32imac -mabi=ilp32"

# Optimization & code gen
OPT_FLAGS="-Os -g"
OPT_FLAGS="${OPT_FLAGS} -fmessage-length=0"
OPT_FLAGS="${OPT_FLAGS} -fsigned-char"
OPT_FLAGS="${OPT_FLAGS} -ffunction-sections -fdata-sections"
OPT_FLAGS="${OPT_FLAGS} -fno-common"

CFLAGS="${ARCH_FLAGS} ${OPT_FLAGS} -Wall"

# ==========================================================================
# Include paths (from MRS2 .cproject)
# ==========================================================================
INCLUDES="-I${PROJECT_ROOT}/StdPeriphDriver/inc"
INCLUDES="${INCLUDES} -I${PROJECT_ROOT}/RVMSIS"
INCLUDES="${INCLUDES} -I${PROJECT_ROOT}/Lib"
INCLUDES="${INCLUDES} -I${PROJECT_ROOT}"

# ==========================================================================
# Linker flags (from MRS2 .cproject)
#   Note: libraries (-lISP583) MUST come AFTER object files
# ==========================================================================
LINK_LIBS="-L${PROJECT_ROOT}/StdPeriphDriver -L${PROJECT_ROOT} -lISP583"
LINKFLAGS="-T${PROJECT_ROOT}/Ld/Link.ld -nostartfiles --specs=nano.specs --specs=nosys.specs -Wl,--gc-sections -Wl,--print-memory-usage"

# ==========================================================================

echo "=== Building CH582F KVM Firmware ==="
echo "Toolchain: ${TOOLCHAIN}"
echo "Build dir: ${BUILD_DIR}"
echo "CFLAGS: ${CFLAGS}"
echo ""

# All C source files (list each individually for clarity)
SOURCES=(
  "src/Main.c"
  "Lib/ws2812b.c"
  "StdPeriphDriver/CH58x_adc.c"
  "StdPeriphDriver/CH58x_clk.c"
  "StdPeriphDriver/CH58x_flash.c"
  "StdPeriphDriver/CH58x_gpio.c"
  "StdPeriphDriver/CH58x_i2c.c"
  "StdPeriphDriver/CH58x_pwm.c"
  "StdPeriphDriver/CH58x_pwr.c"
  "StdPeriphDriver/CH58x_spi0.c"
  "StdPeriphDriver/CH58x_spi1.c"
  "StdPeriphDriver/CH58x_sys.c"
  "StdPeriphDriver/CH58x_timer0.c"
  "StdPeriphDriver/CH58x_timer1.c"
  "StdPeriphDriver/CH58x_timer2.c"
  "StdPeriphDriver/CH58x_timer3.c"
  "StdPeriphDriver/CH58x_uart0.c"
  "StdPeriphDriver/CH58x_uart1.c"
  "StdPeriphDriver/CH58x_uart2.c"
  "StdPeriphDriver/CH58x_uart3.c"
  "StdPeriphDriver/CH58x_usb2dev.c"
  "StdPeriphDriver/CH58x_usb2hostBase.c"
  "StdPeriphDriver/CH58x_usb2hostClass.c"
  "StdPeriphDriver/CH58x_usbdev.c"
  "StdPeriphDriver/CH58x_usbhostBase.c"
  "StdPeriphDriver/CH58x_usbhostClass.c"
  "RVMSIS/core_riscv.c"
)

# Compile C sources
OBJECTS=""
echo "--- Compiling C sources ---"
for src in "${SOURCES[@]}"; do
  rel="${src##*/}"
  obj="${BUILD_DIR}/${rel%.c}.o"
  printf "  CC %-40s" "${src}"
  "${CC}" -c ${CFLAGS} ${INCLUDES} "${PROJECT_ROOT}/${src}" -o "${obj}" 2>&1 && echo "OK" || { echo "FAILED"; exit 1; }
  OBJECTS="${OBJECTS} ${obj}"
done

# Assemble startup file
echo ""
echo "--- Assembling startup ---"
printf "  AS %-40s" "Startup/startup_CH583.S"
"${CC}" -c ${CFLAGS} ${INCLUDES} \
  "${PROJECT_ROOT}/Startup/startup_CH583.S" \
  -o "${BUILD_DIR}/startup_CH583.o" 2>&1 && echo "OK" || { echo "FAILED"; exit 1; }
OBJECTS="${OBJECTS} ${BUILD_DIR}/startup_CH583.o"

# Link
echo ""
echo "--- Linking ---"
"${CC}" ${ARCH_FLAGS} ${OBJECTS} \
  ${LINKFLAGS} \
  ${LINK_LIBS} \
  -o "${BUILD_DIR}/KVM-Card-Mini.elf"

# Generate HEX and BIN
echo ""
echo "--- Generating outputs ---"
"${OBJCOPY}" -O ihex "${BUILD_DIR}/KVM-Card-Mini.elf" "${BUILD_DIR}/KVM-Card-Mini.hex"
"${OBJCOPY}" -O binary "${BUILD_DIR}/KVM-Card-Mini.elf" "${BUILD_DIR}/KVM-Card-Mini.bin"

# Size report
echo ""
echo "--- Size ---"
"${SIZE}" "${BUILD_DIR}/KVM-Card-Mini.elf"

echo ""
echo "=== Build complete ==="
echo "Output:"
echo "  ${BUILD_DIR}/KVM-Card-Mini.hex  (Intel HEX for WCH-Link/WCHISP)"
echo "  ${BUILD_DIR}/KVM-Card-Mini.bin  (Raw binary)"
echo "  ${BUILD_DIR}/KVM-Card-Mini.elf  (ELF with debug info)"
