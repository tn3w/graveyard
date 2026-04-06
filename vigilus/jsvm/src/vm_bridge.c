#include "../quickjs/quickjs.h"
#include "../quickjs/quickjs-libc.h"
#include <emscripten/emscripten.h>
#include <string.h>
#include <stdint.h>

#define TRAP_MAGIC      0xA7B3C1D9u
#define INTEGRITY_SEED  0x5E4F3C2Du
#define MAX_EXEC_COUNT  64
#define TIMING_MAX_US   8000000.0
#define CALL_SEQ_INIT   0xD3ADB33Fu
#define CALL_SEQ_HOST   0x1u
#define CALL_SEQ_TS     0x2u
#define CALL_SEQ_INTEG  0x4u
#define CALL_SEQ_CSUM   0x8u
#define CALL_SEQ_EC     0x10u
#define CALL_SEQ_TRAP   0x20u
#define CALL_SEQ_DBGCHK 0x40u
#define POISON_BYTE     0xDE

static JSRuntime *rt = NULL;
static JSContext *ctx = NULL;
static uint32_t exec_counter = 0;
static uint32_t integrity_acc = INTEGRITY_SEED;
static double first_ts = 0.0;
static double last_ts = 0.0;
static uint32_t call_sequence = CALL_SEQ_INIT;
static uint32_t host_call_count = 0;
static uint32_t ts_call_count = 0;
static uint8_t poisoned = 0;

static void integrity_mix(uint32_t v) {
    integrity_acc ^= v;
    integrity_acc = (integrity_acc << 13)
                  | (integrity_acc >> 19);
    integrity_acc *= 0x5BD1E995u;
}

static uint32_t fnv1a(
    const uint8_t *data, uint32_t len
) {
    uint32_t h = 0x811C9DC5u;
    for (uint32_t i = 0; i < len; i++) {
        h ^= data[i];
        h *= 0x01000193u;
    }
    return h;
}

static void poison_state(void) {
    poisoned = 1;
    integrity_acc = 0xDEADDEADu;
    call_sequence = 0;
}

static JSValue js_vm_timestamp(
    JSContext *c, JSValueConst this_val,
    int argc, JSValueConst *argv
) {
    double now = emscripten_get_now() * 1000.0;

    if (first_ts == 0.0) {
        first_ts = now;
    } else if (now - first_ts > TIMING_MAX_US) {
        poison_state();
    }

    if (last_ts > 0.0) {
        double delta = now - last_ts;
        if (delta < 0.0) poison_state();
        if (delta > 5000000.0 && ts_call_count < 50)
            poison_state();
    }
    last_ts = now;
    ts_call_count++;

    integrity_mix((uint32_t)(uint64_t)now);
    call_sequence |= CALL_SEQ_TS;
    return JS_NewFloat64(c, now);
}

static JSValue js_vm_integrity(
    JSContext *c, JSValueConst this_val,
    int argc, JSValueConst *argv
) {
    call_sequence |= CALL_SEQ_INTEG;
    integrity_mix(call_sequence);
    return JS_NewUint32(c, integrity_acc);
}

EM_JS(const char *, host_eval_js, (const char *code), {
    try {
        var r = (0, eval)(UTF8ToString(code));
        if (r === undefined || r === null) return 0;
        var s = typeof r === "object"
            ? JSON.stringify(r)
            : String(r);
        var len = lengthBytesUTF8(s) + 1;
        var p = _malloc(len);
        stringToUTF8(s, p, len);
        return p;
    } catch (e) {
        return 0;
    }
});

EM_JS(int, host_dbg_check, (void), {
    return 0;
});

static JSValue js_vm_host_call(
    JSContext *c, JSValueConst this_val,
    int argc, JSValueConst *argv
) {
    if (poisoned) return JS_UNDEFINED;
    if (argc < 1) return JS_UNDEFINED;

    const char *code = JS_ToCString(c, argv[0]);
    if (!code) return JS_UNDEFINED;

    host_call_count++;
    integrity_mix(0xCAFE0001u ^ host_call_count);

    if (host_call_count > 200) {
        JS_FreeCString(c, code);
        poison_state();
        return JS_UNDEFINED;
    }

    const char *result = host_eval_js(code);
    JS_FreeCString(c, code);

    if (!result) return JS_UNDEFINED;

    call_sequence |= CALL_SEQ_HOST;

    JSValue ret = JS_NewString(c, result);
    free((void *)result);
    return ret;
}

static JSValue js_vm_mem_checksum(
    JSContext *c, JSValueConst this_val,
    int argc, JSValueConst *argv
) {
    uint32_t offset, length;
    if (argc < 2) return JS_UNDEFINED;
    JS_ToUint32(c, &offset, argv[0]);
    JS_ToUint32(c, &length, argv[1]);

    extern unsigned char __heap_base;
    const uint8_t *base = &__heap_base;
    uint32_t csum = fnv1a(
        base + offset,
        length < 4096 ? length : 4096
    );
    integrity_mix(csum);
    call_sequence |= CALL_SEQ_CSUM;
    return JS_NewUint32(c, csum);
}

static JSValue js_vm_exec_count(
    JSContext *c, JSValueConst this_val,
    int argc, JSValueConst *argv
) {
    call_sequence |= CALL_SEQ_EC;
    return JS_NewUint32(c, exec_counter);
}

static JSValue js_vm_dbg_trap(
    JSContext *c, JSValueConst this_val,
    int argc, JSValueConst *argv
) {
    if (poisoned) return JS_NewInt32(c, -1);

    double now = emscripten_get_now() * 1000.0;
    last_ts = now;

    integrity_mix(0xBAADF00Du);
    call_sequence |= CALL_SEQ_TRAP;
    return JS_NewInt32(c, 0);
}

static JSValue js_vm_dbg_check(
    JSContext *c, JSValueConst this_val,
    int argc, JSValueConst *argv
) {
    if (poisoned) return JS_NewUint32(c, 0xDEADu);

    uint32_t expected_mask =
        CALL_SEQ_INIT | CALL_SEQ_TS | CALL_SEQ_HOST;
    uint32_t present =
        call_sequence & expected_mask;

    if (present != expected_mask) {
        poison_state();
        return JS_NewUint32(c, 0);
    }

    if (host_call_count < 5) {
        poison_state();
        return JS_NewUint32(c, 0);
    }

    uint32_t canary_data[4] = {
        integrity_acc,
        exec_counter,
        host_call_count,
        call_sequence,
    };
    uint32_t canary = fnv1a(
        (const uint8_t *)canary_data,
        sizeof(canary_data)
    );

    integrity_mix(canary);
    call_sequence |= CALL_SEQ_DBGCHK;
    return JS_NewUint32(c, canary);
}

static JSValue js_vm_code_csum(
    JSContext *c, JSValueConst this_val,
    int argc, JSValueConst *argv
) {
    extern unsigned char __data_end;
    extern unsigned char __heap_base;

    const uint8_t *start = &__data_end;
    const uint8_t *end = &__heap_base;
    uint32_t len = (uint32_t)(end - start);
    if (len > 65536) len = 65536;

    uint32_t csum = fnv1a(start, len);
    integrity_mix(csum);
    return JS_NewUint32(c, csum);
}

static void register_vm_intrinsics(JSContext *c) {
    JSValue global = JS_GetGlobalObject(c);

    JS_SetPropertyStr(c, global, "__vm_ts",
        JS_NewCFunction(c, js_vm_timestamp,
                        "__vm_ts", 0));

    JS_SetPropertyStr(c, global, "__vm_integrity",
        JS_NewCFunction(c, js_vm_integrity,
                        "__vm_integrity", 0));

    JS_SetPropertyStr(c, global, "__vm_host",
        JS_NewCFunction(c, js_vm_host_call,
                        "__vm_host", 1));

    JS_SetPropertyStr(c, global, "__vm_csum",
        JS_NewCFunction(c, js_vm_mem_checksum,
                        "__vm_csum", 2));

    JS_SetPropertyStr(c, global, "__vm_ec",
        JS_NewCFunction(c, js_vm_exec_count,
                        "__vm_ec", 0));

    JS_SetPropertyStr(c, global, "__vm_trap",
        JS_NewCFunction(c, js_vm_dbg_trap,
                        "__vm_trap", 0));

    JS_SetPropertyStr(c, global, "__vm_chk",
        JS_NewCFunction(c, js_vm_dbg_check,
                        "__vm_chk", 0));

    JS_SetPropertyStr(c, global, "__vm_ccode",
        JS_NewCFunction(c, js_vm_code_csum,
                        "__vm_ccode", 0));

    JS_FreeValue(c, global);
}

EMSCRIPTEN_KEEPALIVE
int vm_init(void) {
    if (rt) return 0;

    rt = JS_NewRuntime();
    if (!rt) return -1;

    JS_SetMemoryLimit(rt, 16 * 1024 * 1024);
    JS_SetMaxStackSize(rt, 512 * 1024);

    ctx = JS_NewContext(rt);
    if (!ctx) {
        JS_FreeRuntime(rt);
        rt = NULL;
        return -1;
    }

    register_vm_intrinsics(ctx);

    integrity_mix(TRAP_MAGIC);
    exec_counter = 0;
    first_ts = 0.0;
    last_ts = 0.0;
    call_sequence = CALL_SEQ_INIT;
    host_call_count = 0;
    ts_call_count = 0;
    poisoned = 0;
    return 0;
}

EMSCRIPTEN_KEEPALIVE
void vm_destroy(void) {
    if (ctx) { JS_FreeContext(ctx); ctx = NULL; }
    if (rt)  { JS_FreeRuntime(rt);  rt = NULL;  }

    if (poisoned) {
        volatile uint32_t *p =
            (volatile uint32_t *)&integrity_acc;
        *p = 0;
    }
    integrity_acc = INTEGRITY_SEED;
    exec_counter = 0;
    first_ts = 0.0;
    last_ts = 0.0;
    call_sequence = CALL_SEQ_INIT;
    host_call_count = 0;
    ts_call_count = 0;
    poisoned = 0;
}

EMSCRIPTEN_KEEPALIVE
const char *vm_exec_bytecode(
    const uint8_t *bytecode, int length
) {
    if (!ctx || !bytecode || length <= 0) return NULL;
    if (exec_counter >= MAX_EXEC_COUNT) return NULL;
    if (poisoned) return NULL;

    uint32_t bc_hash = fnv1a(bytecode, (uint32_t)length);
    integrity_mix(bc_hash);

    exec_counter++;
    integrity_mix(
        (uint32_t)length ^ (uint32_t)exec_counter
    );

    JSValue obj = JS_ReadObject(
        ctx, bytecode, (size_t)length,
        JS_READ_OBJ_BYTECODE
    );
    if (JS_IsException(obj)) return NULL;

    JSValue result = JS_EvalFunction(ctx, obj);

    if (JS_IsException(result)) {
        JS_FreeValue(ctx, result);
        return NULL;
    }

    if (poisoned) {
        JS_FreeValue(ctx, result);
        return NULL;
    }

    const char *str = JS_ToCString(ctx, result);
    JS_FreeValue(ctx, result);

    if (!str) return NULL;

    size_t slen = strlen(str);
    char *out = (char *)malloc(slen + 1);
    if (out) memcpy(out, str, slen + 1);
    JS_FreeCString(ctx, str);

    return out;
}

EMSCRIPTEN_KEEPALIVE
void vm_free(void *ptr) {
    free(ptr);
}
