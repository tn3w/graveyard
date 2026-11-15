#ifndef RUNNER_MPRIS_PLUGIN_H_
#define RUNNER_MPRIS_PLUGIN_H_

#include <flutter_linux/flutter_linux.h>
#include <gio/gio.h>

#include <memory>
#include <string>

G_BEGIN_DECLS

#define MPRIS_TYPE_PLUGIN mpris_plugin_get_type()
G_DECLARE_FINAL_TYPE(MprisPlugin, mpris_plugin, MPRIS, PLUGIN, GObject)

MprisPlugin* mpris_plugin_new(FlPluginRegistrar* registrar);

void mpris_plugin_register_with_registrar(FlPluginRegistrar* registrar);

G_END_DECLS

#endif  // RUNNER_MPRIS_PLUGIN_H_
