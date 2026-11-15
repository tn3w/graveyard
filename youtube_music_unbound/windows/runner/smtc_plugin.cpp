#include "smtc_plugin.h"

#include <flutter/method_channel.h>
#include <flutter/standard_method_codec.h>
#include <flutter/event_channel.h>
#include <flutter_messenger.h>
#include "../flutter/ephemeral/cpp_client_wrapper/binary_messenger_impl.h"

#include <memory>
#include <sstream>

namespace {
  // Keep these alive for the lifetime of the application
  static std::shared_ptr<SmtcPlugin> plugin_instance;
  static std::shared_ptr<flutter::BinaryMessengerImpl> messenger_wrapper;
}

// C API wrapper
void SmtcPluginRegisterWithRegistrar(
    FlutterDesktopPluginRegistrarRef registrar_ref) {
  try {
    plugin_instance = std::make_shared<SmtcPlugin>();

    auto messenger_ref = FlutterDesktopPluginRegistrarGetMessenger(registrar_ref);
    if (!messenger_ref) {
      return;
    }
    
    messenger_wrapper = std::make_shared<flutter::BinaryMessengerImpl>(messenger_ref);
    
    auto channel = std::make_unique<flutter::MethodChannel<flutter::EncodableValue>>(
        messenger_wrapper.get(), "youtube_music_unbound/smtc",
        &flutter::StandardMethodCodec::GetInstance());

    channel->SetMethodCallHandler(
        [](const auto& call, auto result) {
          if (plugin_instance) {
            plugin_instance->HandleMethodCall(call, std::move(result));
          }
        });

    plugin_instance->SetChannel(std::move(channel));
  } catch (...) {
    // Plugin registration failed, continue without SMTC support
  }
}

void SmtcPlugin::SetChannel(std::unique_ptr<flutter::MethodChannel<flutter::EncodableValue>> channel) {
  channel_ = std::move(channel);
}

SmtcPlugin::SmtcPlugin() {}

SmtcPlugin::~SmtcPlugin() {
  if (smtc_) {
    smtc_.IsEnabled(false);
    smtc_ = nullptr;
  }
}

void SmtcPlugin::HandleMethodCall(
    const flutter::MethodCall<flutter::EncodableValue>& method_call,
    std::unique_ptr<flutter::MethodResult<flutter::EncodableValue>> result) {
  const std::string& method = method_call.method_name();

  if (method == "initialize") {
    InitializeSmtc();
    result->Success(flutter::EncodableValue(true));
  } else if (method == "updateMetadata") {
    const auto* arguments = std::get_if<flutter::EncodableMap>(
        method_call.arguments());
    if (arguments) {
      UpdateMetadata(*arguments);
      result->Success();
    } else {
      result->Error("INVALID_ARGUMENT", "Expected map argument");
    }
  } else if (method == "updatePlaybackState") {
    const auto* arguments = std::get_if<flutter::EncodableMap>(
        method_call.arguments());
    if (arguments) {
      auto state_it = arguments->find(flutter::EncodableValue("state"));
      if (state_it != arguments->end()) {
        const auto* state = std::get_if<std::string>(&state_it->second);
        if (state) {
          UpdatePlaybackState(*state);
          result->Success();
        } else {
          result->Error("INVALID_ARGUMENT", "State must be a string");
        }
      } else {
        result->Error("INVALID_ARGUMENT", "Missing state argument");
      }
    } else {
      result->Error("INVALID_ARGUMENT", "Expected map argument");
    }
  } else if (method == "setPlaybackPosition") {
    const auto* arguments = std::get_if<flutter::EncodableMap>(
        method_call.arguments());
    if (arguments) {
      auto position_it = arguments->find(flutter::EncodableValue("position"));
      auto duration_it = arguments->find(flutter::EncodableValue("duration"));
      
      if (position_it != arguments->end() && duration_it != arguments->end()) {
        const auto* position = std::get_if<int64_t>(&position_it->second);
        const auto* duration = std::get_if<int64_t>(&duration_it->second);
        
        if (position && duration) {
          SetPlaybackPosition(*position, *duration);
          result->Success();
        } else {
          result->Error("INVALID_ARGUMENT", 
                       "Position and duration must be integers");
        }
      } else {
        result->Error("INVALID_ARGUMENT", 
                     "Missing position or duration argument");
      }
    } else {
      result->Error("INVALID_ARGUMENT", "Expected map argument");
    }
  } else {
    result->NotImplemented();
  }
}

void SmtcPlugin::InitializeSmtc() {
  if (is_initialized_) {
    return;
  }

  try {
    smtc_ = SystemMediaTransportControls::GetForCurrentView();
    smtc_.IsEnabled(true);
    smtc_.IsPlayEnabled(true);
    smtc_.IsPauseEnabled(true);
    smtc_.IsNextEnabled(true);
    smtc_.IsPreviousEnabled(true);
    smtc_.IsStopEnabled(true);

    display_updater_ = smtc_.DisplayUpdater();
    display_updater_.Type(MediaPlaybackType::Music);

    smtc_.ButtonPressed([this](
        SystemMediaTransportControls const&,
        SystemMediaTransportControlsButtonPressedEventArgs const& args) {
      std::string command;
      switch (args.Button()) {
        case SystemMediaTransportControlsButton::Play:
          command = "play";
          break;
        case SystemMediaTransportControlsButton::Pause:
          command = "pause";
          break;
        case SystemMediaTransportControlsButton::Next:
          command = "next";
          break;
        case SystemMediaTransportControlsButton::Previous:
          command = "previous";
          break;
        case SystemMediaTransportControlsButton::Stop:
          command = "stop";
          break;
        default:
          return;
      }

      if (channel_) {
        flutter::EncodableMap args_map;
        args_map[flutter::EncodableValue("command")] = 
            flutter::EncodableValue(command);
        channel_->InvokeMethod("onMediaCommand", 
            std::make_unique<flutter::EncodableValue>(args_map));
      }
    });

    is_initialized_ = true;
  } catch (...) {
    // SMTC initialization failed, continue without media controls
  }
}

void SmtcPlugin::UpdateMetadata(const flutter::EncodableMap& metadata) {
  if (!is_initialized_ || !display_updater_) {
    return;
  }

  try {
    auto music_properties = display_updater_.MusicProperties();

    auto title_it = metadata.find(flutter::EncodableValue("title"));
    if (title_it != metadata.end()) {
      const auto* title = std::get_if<std::string>(&title_it->second);
      if (title) {
        music_properties.Title(winrt::to_hstring(*title));
      }
    }

    auto artist_it = metadata.find(flutter::EncodableValue("artist"));
    if (artist_it != metadata.end()) {
      const auto* artist = std::get_if<std::string>(&artist_it->second);
      if (artist) {
        music_properties.Artist(winrt::to_hstring(*artist));
      }
    }

    auto album_it = metadata.find(flutter::EncodableValue("album"));
    if (album_it != metadata.end()) {
      const auto* album = std::get_if<std::string>(&album_it->second);
      if (album && !album->empty()) {
        music_properties.AlbumTitle(winrt::to_hstring(*album));
      }
    }

    auto artwork_it = metadata.find(flutter::EncodableValue("artworkUrl"));
    if (artwork_it != metadata.end()) {
      const auto* artwork_url = std::get_if<std::string>(&artwork_it->second);
      if (artwork_url && !artwork_url->empty()) {
        try {
          auto uri = winrt::Windows::Foundation::Uri(
              winrt::to_hstring(*artwork_url));
          display_updater_.Thumbnail(
              RandomAccessStreamReference::CreateFromUri(uri));
        } catch (...) {
          // Artwork URL invalid, continue without thumbnail
        }
      }
    }

    display_updater_.Update();
  } catch (...) {
    // Metadata update failed, continue
  }
}

void SmtcPlugin::UpdatePlaybackState(const std::string& state) {
  if (!is_initialized_ || !smtc_) {
    return;
  }

  try {
    MediaPlaybackStatus status;
    if (state == "playing") {
      status = MediaPlaybackStatus::Playing;
    } else if (state == "paused") {
      status = MediaPlaybackStatus::Paused;
    } else if (state == "stopped") {
      status = MediaPlaybackStatus::Stopped;
    } else {
      status = MediaPlaybackStatus::Closed;
    }

    smtc_.PlaybackStatus(status);
  } catch (...) {
    // Playback state update failed, continue
  }
}

void SmtcPlugin::SetPlaybackPosition(int64_t position_ms, 
                                     int64_t duration_ms) {
  if (!is_initialized_ || !smtc_) {
    return;
  }

  try {
    auto timeline_properties = SystemMediaTransportControlsTimelineProperties();
    
    timeline_properties.StartTime(winrt::Windows::Foundation::TimeSpan(0));
    timeline_properties.Position(
        winrt::Windows::Foundation::TimeSpan(position_ms * 10000));
    timeline_properties.EndTime(
        winrt::Windows::Foundation::TimeSpan(duration_ms * 10000));

    smtc_.UpdateTimelineProperties(timeline_properties);
  } catch (...) {
    // Timeline update failed, continue
  }
}
