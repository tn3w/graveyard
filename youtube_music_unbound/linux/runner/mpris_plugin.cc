#include "mpris_plugin.h"

#include <flutter_linux/flutter_linux.h>
#include <gio/gio.h>

#include <cstring>

static constexpr char kChannelName[] = "youtube_music_unbound/mpris";
static constexpr char kBusName[] = "org.mpris.MediaPlayer2.YouTubeMusicUnbound";
static constexpr char kObjectPath[] = "/org/mpris/MediaPlayer2";

static constexpr char kMprisInterface[] = 
    "org.mpris.MediaPlayer2";
static constexpr char kMprisPlayerInterface[] = 
    "org.mpris.MediaPlayer2.Player";

static constexpr char kIntrospectionXml[] =
    "<node>"
    "  <interface name='org.mpris.MediaPlayer2'>"
    "    <method name='Raise'/>"
    "    <method name='Quit'/>"
    "    <property name='CanQuit' type='b' access='read'/>"
    "    <property name='CanRaise' type='b' access='read'/>"
    "    <property name='HasTrackList' type='b' access='read'/>"
    "    <property name='Identity' type='s' access='read'/>"
    "    <property name='SupportedUriSchemes' type='as' access='read'/>"
    "    <property name='SupportedMimeTypes' type='as' access='read'/>"
    "  </interface>"
    "  <interface name='org.mpris.MediaPlayer2.Player'>"
    "    <method name='Next'/>"
    "    <method name='Previous'/>"
    "    <method name='Pause'/>"
    "    <method name='PlayPause'/>"
    "    <method name='Stop'/>"
    "    <method name='Play'/>"
    "    <method name='Seek'>"
    "      <arg direction='in' name='Offset' type='x'/>"
    "    </method>"
    "    <method name='SetPosition'>"
    "      <arg direction='in' name='TrackId' type='o'/>"
    "      <arg direction='in' name='Position' type='x'/>"
    "    </method>"
    "    <property name='PlaybackStatus' type='s' access='read'/>"
    "    <property name='Rate' type='d' access='readwrite'/>"
    "    <property name='Metadata' type='a{sv}' access='read'/>"
    "    <property name='Volume' type='d' access='readwrite'/>"
    "    <property name='Position' type='x' access='read'/>"
    "    <property name='MinimumRate' type='d' access='read'/>"
    "    <property name='MaximumRate' type='d' access='read'/>"
    "    <property name='CanGoNext' type='b' access='read'/>"
    "    <property name='CanGoPrevious' type='b' access='read'/>"
    "    <property name='CanPlay' type='b' access='read'/>"
    "    <property name='CanPause' type='b' access='read'/>"
    "    <property name='CanSeek' type='b' access='read'/>"
    "    <property name='CanControl' type='b' access='read'/>"
    "  </interface>"
    "</node>";

struct _MprisPlugin {
  GObject parent_instance;
  
  FlMethodChannel* channel;
  GDBusConnection* connection;
  guint bus_id;
  guint registration_id;
  GDBusNodeInfo* introspection_data;
  
  gchar* playback_status;
  GHashTable* metadata;
  gint64 position;
  gint64 duration;
};

G_DEFINE_TYPE(MprisPlugin, mpris_plugin, G_TYPE_OBJECT)

static void send_command_to_flutter(MprisPlugin* self, const gchar* command);
static void handle_method_call(FlMethodChannel* channel,
                               FlMethodCall* method_call,
                               gpointer user_data);

static void mpris_plugin_dispose(GObject* object) {
  MprisPlugin* self = MPRIS_PLUGIN(object);
  
  if (self->registration_id > 0) {
    g_dbus_connection_unregister_object(self->connection, 
                                       self->registration_id);
    self->registration_id = 0;
  }
  
  if (self->bus_id > 0) {
    g_bus_unown_name(self->bus_id);
    self->bus_id = 0;
  }
  
  g_clear_object(&self->connection);
  g_clear_object(&self->channel);
  g_clear_pointer(&self->introspection_data, g_dbus_node_info_unref);
  g_clear_pointer(&self->playback_status, g_free);
  g_clear_pointer(&self->metadata, g_hash_table_unref);
  
  G_OBJECT_CLASS(mpris_plugin_parent_class)->dispose(object);
}

static void mpris_plugin_class_init(MprisPluginClass* klass) {
  G_OBJECT_CLASS(klass)->dispose = mpris_plugin_dispose;
}

static void mpris_plugin_init(MprisPlugin* self) {
  self->playback_status = g_strdup("Stopped");
  self->metadata = g_hash_table_new_full(g_str_hash, g_str_equal,
                                         g_free, 
                                         (GDestroyNotify)g_variant_unref);
  self->position = 0;
  self->duration = 0;
}

static void handle_mpris_method_call(
    GDBusConnection* connection,
    const gchar* sender,
    const gchar* object_path,
    const gchar* interface_name,
    const gchar* method_name,
    GVariant* parameters,
    GDBusMethodInvocation* invocation,
    gpointer user_data) {
  
  MprisPlugin* self = MPRIS_PLUGIN(user_data);
  
  if (g_strcmp0(interface_name, kMprisPlayerInterface) == 0) {
    if (g_strcmp0(method_name, "Play") == 0) {
      send_command_to_flutter(self, "play");
      g_dbus_method_invocation_return_value(invocation, nullptr);
    } else if (g_strcmp0(method_name, "Pause") == 0) {
      send_command_to_flutter(self, "pause");
      g_dbus_method_invocation_return_value(invocation, nullptr);
    } else if (g_strcmp0(method_name, "PlayPause") == 0) {
      send_command_to_flutter(self, "play");
      g_dbus_method_invocation_return_value(invocation, nullptr);
    } else if (g_strcmp0(method_name, "Next") == 0) {
      send_command_to_flutter(self, "next");
      g_dbus_method_invocation_return_value(invocation, nullptr);
    } else if (g_strcmp0(method_name, "Previous") == 0) {
      send_command_to_flutter(self, "previous");
      g_dbus_method_invocation_return_value(invocation, nullptr);
    } else if (g_strcmp0(method_name, "Stop") == 0) {
      send_command_to_flutter(self, "stop");
      g_dbus_method_invocation_return_value(invocation, nullptr);
    } else {
      g_dbus_method_invocation_return_error(
          invocation, G_DBUS_ERROR, G_DBUS_ERROR_NOT_SUPPORTED,
          "Method not supported");
    }
  } else if (g_strcmp0(interface_name, kMprisInterface) == 0) {
    if (g_strcmp0(method_name, "Raise") == 0 ||
        g_strcmp0(method_name, "Quit") == 0) {
      g_dbus_method_invocation_return_value(invocation, nullptr);
    } else {
      g_dbus_method_invocation_return_error(
          invocation, G_DBUS_ERROR, G_DBUS_ERROR_NOT_SUPPORTED,
          "Method not supported");
    }
  }
}

static GVariant* handle_mpris_get_property(
    GDBusConnection* connection,
    const gchar* sender,
    const gchar* object_path,
    const gchar* interface_name,
    const gchar* property_name,
    GError** error,
    gpointer user_data) {
  
  MprisPlugin* self = MPRIS_PLUGIN(user_data);
  
  if (g_strcmp0(interface_name, kMprisPlayerInterface) == 0) {
    if (g_strcmp0(property_name, "PlaybackStatus") == 0) {
      return g_variant_new_string(self->playback_status);
    } else if (g_strcmp0(property_name, "Metadata") == 0) {
      GVariantBuilder builder;
      g_variant_builder_init(&builder, G_VARIANT_TYPE("a{sv}"));
      
      GHashTableIter iter;
      gpointer key, value;
      g_hash_table_iter_init(&iter, self->metadata);
      while (g_hash_table_iter_next(&iter, &key, &value)) {
        g_variant_builder_add(&builder, "{sv}", 
                            (const gchar*)key, 
                            (GVariant*)value);
      }
      
      return g_variant_builder_end(&builder);
    } else if (g_strcmp0(property_name, "Position") == 0) {
      return g_variant_new_int64(self->position);
    } else if (g_strcmp0(property_name, "CanGoNext") == 0) {
      return g_variant_new_boolean(TRUE);
    } else if (g_strcmp0(property_name, "CanGoPrevious") == 0) {
      return g_variant_new_boolean(TRUE);
    } else if (g_strcmp0(property_name, "CanPlay") == 0) {
      return g_variant_new_boolean(TRUE);
    } else if (g_strcmp0(property_name, "CanPause") == 0) {
      return g_variant_new_boolean(TRUE);
    } else if (g_strcmp0(property_name, "CanSeek") == 0) {
      return g_variant_new_boolean(FALSE);
    } else if (g_strcmp0(property_name, "CanControl") == 0) {
      return g_variant_new_boolean(TRUE);
    } else if (g_strcmp0(property_name, "Rate") == 0) {
      return g_variant_new_double(1.0);
    } else if (g_strcmp0(property_name, "MinimumRate") == 0) {
      return g_variant_new_double(1.0);
    } else if (g_strcmp0(property_name, "MaximumRate") == 0) {
      return g_variant_new_double(1.0);
    } else if (g_strcmp0(property_name, "Volume") == 0) {
      return g_variant_new_double(1.0);
    }
  } else if (g_strcmp0(interface_name, kMprisInterface) == 0) {
    if (g_strcmp0(property_name, "CanQuit") == 0) {
      return g_variant_new_boolean(TRUE);
    } else if (g_strcmp0(property_name, "CanRaise") == 0) {
      return g_variant_new_boolean(TRUE);
    } else if (g_strcmp0(property_name, "HasTrackList") == 0) {
      return g_variant_new_boolean(FALSE);
    } else if (g_strcmp0(property_name, "Identity") == 0) {
      return g_variant_new_string("YouTube Music Unbound");
    } else if (g_strcmp0(property_name, "SupportedUriSchemes") == 0) {
      const gchar* schemes[] = {nullptr};
      return g_variant_new_strv(schemes, 0);
    } else if (g_strcmp0(property_name, "SupportedMimeTypes") == 0) {
      const gchar* types[] = {nullptr};
      return g_variant_new_strv(types, 0);
    }
  }
  
  g_set_error(error, G_DBUS_ERROR, G_DBUS_ERROR_NOT_SUPPORTED,
              "Property not supported");
  return nullptr;
}

static const GDBusInterfaceVTable interface_vtable = {
  handle_mpris_method_call,
  handle_mpris_get_property,
  nullptr
};

static void on_bus_acquired(GDBusConnection* connection,
                           const gchar* name,
                           gpointer user_data) {
  MprisPlugin* self = MPRIS_PLUGIN(user_data);
  GError* error = nullptr;
  
  self->connection = G_DBUS_CONNECTION(g_object_ref(connection));
  
  self->registration_id = g_dbus_connection_register_object(
      connection,
      kObjectPath,
      self->introspection_data->interfaces[0],
      &interface_vtable,
      self,
      nullptr,
      &error);
  
  if (self->registration_id == 0) {
    g_warning("Failed to register MPRIS interface: %s", error->message);
    g_error_free(error);
    return;
  }
  
  g_dbus_connection_register_object(
      connection,
      kObjectPath,
      self->introspection_data->interfaces[1],
      &interface_vtable,
      self,
      nullptr,
      nullptr);
}

static void send_command_to_flutter(MprisPlugin* self, const gchar* command) {
  g_autoptr(FlValue) args = fl_value_new_map();
  fl_value_set_string_take(args, "command", fl_value_new_string(command));
  
  fl_method_channel_invoke_method(self->channel, "onMediaCommand", args,
                                 nullptr, nullptr, nullptr);
}

static void initialize_mpris(MprisPlugin* self) {
  GError* error = nullptr;
  
  self->introspection_data = g_dbus_node_info_new_for_xml(
      kIntrospectionXml, &error);
  
  if (error != nullptr) {
    g_warning("Failed to parse introspection XML: %s", error->message);
    g_error_free(error);
    return;
  }
  
  self->bus_id = g_bus_own_name(
      G_BUS_TYPE_SESSION,
      kBusName,
      G_BUS_NAME_OWNER_FLAGS_NONE,
      on_bus_acquired,
      nullptr,
      nullptr,
      self,
      nullptr);
}

static void update_metadata(MprisPlugin* self, FlValue* args) {
  g_hash_table_remove_all(self->metadata);
  
  FlValue* title = fl_value_lookup_string(args, "title");
  if (title != nullptr && fl_value_get_type(title) == FL_VALUE_TYPE_STRING) {
    g_hash_table_insert(self->metadata,
                       g_strdup("xesam:title"),
                       g_variant_ref_sink(g_variant_new_string(
                           fl_value_get_string(title))));
  }
  
  FlValue* artist = fl_value_lookup_string(args, "artist");
  if (artist != nullptr && fl_value_get_type(artist) == FL_VALUE_TYPE_STRING) {
    const gchar* artists[] = {fl_value_get_string(artist), nullptr};
    g_hash_table_insert(self->metadata,
                       g_strdup("xesam:artist"),
                       g_variant_ref_sink(g_variant_new_strv(artists, 1)));
  }
  
  FlValue* album = fl_value_lookup_string(args, "album");
  if (album != nullptr && fl_value_get_type(album) == FL_VALUE_TYPE_STRING) {
    const gchar* album_str = fl_value_get_string(album);
    if (strlen(album_str) > 0) {
      g_hash_table_insert(self->metadata,
                         g_strdup("xesam:album"),
                         g_variant_ref_sink(g_variant_new_string(album_str)));
    }
  }
  
  FlValue* artwork_url = fl_value_lookup_string(args, "artworkUrl");
  if (artwork_url != nullptr && 
      fl_value_get_type(artwork_url) == FL_VALUE_TYPE_STRING) {
    const gchar* url = fl_value_get_string(artwork_url);
    if (strlen(url) > 0) {
      g_hash_table_insert(self->metadata,
                         g_strdup("mpris:artUrl"),
                         g_variant_ref_sink(g_variant_new_string(url)));
    }
  }
  
  g_hash_table_insert(self->metadata,
                     g_strdup("mpris:trackid"),
                     g_variant_ref_sink(g_variant_new_object_path(
                         "/org/mpris/MediaPlayer2/Track/1")));
  
  if (self->connection != nullptr) {
    GVariantBuilder builder;
    g_variant_builder_init(&builder, G_VARIANT_TYPE("a{sv}"));
    g_variant_builder_add(&builder, "{sv}", "Metadata",
                         handle_mpris_get_property(
                             self->connection, nullptr, nullptr,
                             kMprisPlayerInterface, "Metadata",
                             nullptr, self));
    
    g_dbus_connection_emit_signal(
        self->connection,
        nullptr,
        kObjectPath,
        "org.freedesktop.DBus.Properties",
        "PropertiesChanged",
        g_variant_new("(sa{sv}as)", kMprisPlayerInterface, &builder, nullptr),
        nullptr);
  }
}

static void update_playback_state(MprisPlugin* self, FlValue* args) {
  FlValue* state = fl_value_lookup_string(args, "state");
  if (state == nullptr || fl_value_get_type(state) != FL_VALUE_TYPE_STRING) {
    return;
  }
  
  const gchar* state_str = fl_value_get_string(state);
  g_free(self->playback_status);
  
  if (g_strcmp0(state_str, "playing") == 0) {
    self->playback_status = g_strdup("Playing");
  } else if (g_strcmp0(state_str, "paused") == 0) {
    self->playback_status = g_strdup("Paused");
  } else {
    self->playback_status = g_strdup("Stopped");
  }
  
  if (self->connection != nullptr) {
    GVariantBuilder builder;
    g_variant_builder_init(&builder, G_VARIANT_TYPE("a{sv}"));
    g_variant_builder_add(&builder, "{sv}", "PlaybackStatus",
                         g_variant_new_string(self->playback_status));
    
    g_dbus_connection_emit_signal(
        self->connection,
        nullptr,
        kObjectPath,
        "org.freedesktop.DBus.Properties",
        "PropertiesChanged",
        g_variant_new("(sa{sv}as)", kMprisPlayerInterface, &builder, nullptr),
        nullptr);
  }
}

static void set_playback_position(MprisPlugin* self, FlValue* args) {
  FlValue* position = fl_value_lookup_string(args, "position");
  FlValue* duration = fl_value_lookup_string(args, "duration");
  
  if (position != nullptr && fl_value_get_type(position) == FL_VALUE_TYPE_INT) {
    self->position = fl_value_get_int(position);
  }
  
  if (duration != nullptr && fl_value_get_type(duration) == FL_VALUE_TYPE_INT) {
    self->duration = fl_value_get_int(duration);
    
    g_hash_table_insert(self->metadata,
                       g_strdup("mpris:length"),
                       g_variant_ref_sink(g_variant_new_int64(self->duration)));
  }
}

static void handle_method_call(FlMethodChannel* channel,
                               FlMethodCall* method_call,
                               gpointer user_data) {
  MprisPlugin* self = MPRIS_PLUGIN(user_data);
  
  const gchar* method = fl_method_call_get_name(method_call);
  FlValue* args = fl_method_call_get_args(method_call);
  
  g_autoptr(FlMethodResponse) response = nullptr;
  
  if (g_strcmp0(method, "initialize") == 0) {
    initialize_mpris(self);
    response = FL_METHOD_RESPONSE(fl_method_success_response_new(
        fl_value_new_bool(TRUE)));
  } else if (g_strcmp0(method, "updateMetadata") == 0) {
    update_metadata(self, args);
    response = FL_METHOD_RESPONSE(fl_method_success_response_new(nullptr));
  } else if (g_strcmp0(method, "updatePlaybackState") == 0) {
    update_playback_state(self, args);
    response = FL_METHOD_RESPONSE(fl_method_success_response_new(nullptr));
  } else if (g_strcmp0(method, "setPlaybackPosition") == 0) {
    set_playback_position(self, args);
    response = FL_METHOD_RESPONSE(fl_method_success_response_new(nullptr));
  } else {
    response = FL_METHOD_RESPONSE(fl_method_not_implemented_response_new());
  }
  
  fl_method_call_respond(method_call, response, nullptr);
}

MprisPlugin* mpris_plugin_new(FlPluginRegistrar* registrar) {
  MprisPlugin* self = MPRIS_PLUGIN(
      g_object_new(mpris_plugin_get_type(), nullptr));
  
  g_autoptr(FlStandardMethodCodec) codec = fl_standard_method_codec_new();
  self->channel = fl_method_channel_new(
      fl_plugin_registrar_get_messenger(registrar),
      kChannelName,
      FL_METHOD_CODEC(codec));
  
  fl_method_channel_set_method_call_handler(
      self->channel, handle_method_call, self, nullptr);
  
  return self;
}

void mpris_plugin_register_with_registrar(FlPluginRegistrar* registrar) {
  MprisPlugin* plugin = mpris_plugin_new(registrar);
  g_object_unref(plugin);
}
