# QuickJS → WASM build
# Requires: Emscripten SDK (emsdk)

EMSDK_DIR   ?= $(shell cd .. && pwd)/emsdk
EMSDK_ENV   := $(EMSDK_DIR)/emsdk_env.sh
QJS_DIR     := quickjs
SRC_DIR     := src
BUILD_DIR   := build
OUT_DIR     := public

EXPORTED_FNS := ["_vm_init","_vm_destroy","_vm_exec_bytecode","_vm_free","_malloc","_free"]
EXPORTED_RT  := ["UTF8ToString","HEAPU8"]

EMCC_FLAGS  := \
	-O3 \
	-flto \
	-DCONFIG_VERSION=\"2025-09-13\" \
	-DEMSCRIPTEN \
	-D_GNU_SOURCE \
	-DNO_POPEN \
	-s WASM=1 \
	-s MODULARIZE=1 \
	-s EXPORT_NAME="QJSModule" \
	-s ALLOW_MEMORY_GROWTH=0 \
	-s INITIAL_MEMORY=16777216 \
	-s MAXIMUM_MEMORY=16777216 \
	-s STACK_SIZE=524288 \
	-s NO_EXIT_RUNTIME=1 \
	-s NO_FILESYSTEM=1 \
	-s ENVIRONMENT=web \
	-s EXPORTED_FUNCTIONS='$(EXPORTED_FNS)' \
	-s EXPORTED_RUNTIME_METHODS='$(EXPORTED_RT)' \
	--closure 1

QJS_SRCS := \
	$(QJS_DIR)/quickjs.c \
	$(QJS_DIR)/cutils.c \
	$(QJS_DIR)/libunicode.c \
	$(QJS_DIR)/libregexp.c \
	$(QJS_DIR)/dtoa.c \
	$(QJS_DIR)/quickjs-libc.c

BRIDGE_SRC := $(SRC_DIR)/vm_bridge.c

ALL_SRCS := $(QJS_SRCS) $(BRIDGE_SRC)

.PHONY: all clean

all: $(OUT_DIR)/vm.js $(OUT_DIR)/vm.wasm

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(OUT_DIR):
	mkdir -p $(OUT_DIR)

$(OUT_DIR)/vm.js $(OUT_DIR)/vm.wasm: $(ALL_SRCS) | $(BUILD_DIR) $(OUT_DIR)
	bash -c 'source "$(EMSDK_ENV)" 2>/dev/null && \
		emcc $(EMCC_FLAGS) \
		-I$(QJS_DIR) \
		$(ALL_SRCS) \
		-o $(OUT_DIR)/vm.js'

clean:
	rm -rf $(BUILD_DIR)
	rm -f $(OUT_DIR)/vm.js $(OUT_DIR)/vm.wasm
