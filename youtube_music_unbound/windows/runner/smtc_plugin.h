#ifndef RUNNER_SMTC_PLUGIN_H_
#define RUNNER_SMTC_PLUGIN_H_

#include <flutter/method_channel.h>
#include <flutter/standard_method_codec.h>
#include <flutter_plugin_registrar.h>
#include <windows.h>
#include <systemmediatransportcontrolsinterop.h>
#include <wrl.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Media.h>
#include <winrt/Windows.Storage.Streams.h>

#include <memory>
#include <string>

#ifdef __cplusplus
extern "C" {
#endif

void SmtcPluginRegisterWithRegistrar(
    FlutterDesktopPluginRegistrarRef registrar);

#ifdef __cplusplus
}  // extern "C"
#endif

using namespace Microsoft::WRL;
using namespace winrt::Windows::Media;
using namespace winrt::Windows::Storage::Streams;

class SmtcPlugin {
 public:
  SmtcPlugin();
  virtual ~SmtcPlugin();

  void HandleMethodCall(
      const flutter::MethodCall<flutter::EncodableValue>& method_call,
      std::unique_ptr<flutter::MethodResult<flutter::EncodableValue>> result);

  void SetChannel(std::unique_ptr<flutter::MethodChannel<flutter::EncodableValue>> channel);

 private:
  void InitializeSmtc();
  void UpdateMetadata(const flutter::EncodableMap& metadata);
  void UpdatePlaybackState(const std::string& state);
  void SetPlaybackPosition(int64_t position_ms, int64_t duration_ms);

  std::unique_ptr<flutter::MethodChannel<flutter::EncodableValue>> channel_;
  SystemMediaTransportControls smtc_{nullptr};
  SystemMediaTransportControlsDisplayUpdater display_updater_{nullptr};
  bool is_initialized_ = false;
};

#endif  // RUNNER_SMTC_PLUGIN_H_
