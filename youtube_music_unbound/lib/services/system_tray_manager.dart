import 'dart:io' show Platform;
import 'package:flutter/material.dart';
import 'package:system_tray/system_tray.dart';
import 'package:window_manager/window_manager.dart';
import '../models/media_command.dart';
import '../models/playback_state.dart';

class SystemTrayManager {
  final SystemTray _systemTray = SystemTray();
  final Function(MediaCommand) onMediaCommand;
  final VoidCallback onExit;
  PlaybackState _currentState = PlaybackState.stopped;

  SystemTrayManager({required this.onMediaCommand, required this.onExit});

  Future<void> initialize() async {
    if (!Platform.isWindows && !Platform.isLinux && !Platform.isMacOS) {
      return;
    }

    try {
      await windowManager.ensureInitialized();

      const windowOptions = WindowOptions(
        size: Size(1280, 720),
        minimumSize: Size(800, 600),
        center: true,
        backgroundColor: Colors.transparent,
        skipTaskbar: false,
        titleBarStyle: TitleBarStyle.hidden,
      );

      await windowManager.waitUntilReadyToShow(windowOptions, () async {
        await windowManager.show();
        await windowManager.focus();
      });

      await _initSystemTray();
      await _setupWindowBehavior();
    } catch (e) {
      // Ignore initialization errors
    }
  }

  Future<void> _initSystemTray() async {
    final iconPath = Platform.isWindows
        ? 'assets/icons/icon.ico'
        : 'assets/icons/icon.png';

    await _systemTray.initSystemTray(
      title: 'YouTube Music Unbound',
      iconPath: iconPath,
    );

    await _systemTray.setToolTip('YouTube Music Unbound');
    await _systemTray.setContextMenu(_buildContextMenu());

    _systemTray.registerSystemTrayEventHandler((eventName) {
      if (eventName == kSystemTrayEventClick) {
        _handleTrayClick();
      } else if (eventName == kSystemTrayEventRightClick) {
        _systemTray.popUpContextMenu();
      }
    });
  }

  Future<void> _setupWindowBehavior() async {
    windowManager.addListener(_WindowListener(onClose: _handleWindowClose));
  }

  void _handleTrayClick() async {
    final isVisible = await windowManager.isVisible();
    if (isVisible) {
      await windowManager.hide();
    } else {
      await windowManager.show();
      await windowManager.focus();
    }
  }

  Future<void> _handleWindowClose() async {
    await windowManager.hide();
  }

  Menu _buildContextMenu() {
    final playPauseLabel = _currentState == PlaybackState.playing
        ? 'Pause'
        : 'Play';

    final menu = Menu();
    menu.buildFrom([
      MenuItemLabel(
        label: playPauseLabel,
        onClicked: (menuItem) => onMediaCommand(MediaCommand.playPause),
      ),
      MenuItemLabel(
        label: 'Next',
        onClicked: (menuItem) => onMediaCommand(MediaCommand.next),
      ),
      MenuSeparator(),
      MenuItemLabel(
        label: 'Show/Hide',
        onClicked: (menuItem) => _handleTrayClick(),
      ),
      MenuSeparator(),
      MenuItemLabel(label: 'Exit', onClicked: (menuItem) => onExit()),
    ]);

    return menu;
  }

  Future<void> updatePlaybackState(PlaybackState state) async {
    if (_currentState == state) return;

    _currentState = state;

    try {
      await _systemTray.setContextMenu(_buildContextMenu());
    } catch (e) {
      // Ignore menu update errors
    }
  }

  Future<void> dispose() async {
    try {
      await _systemTray.destroy();
    } catch (e) {
      // Ignore disposal errors
    }
  }
}

class _WindowListener extends WindowListener {
  final Future<void> Function() onClose;

  _WindowListener({required this.onClose});

  @override
  void onWindowClose() {
    onClose();
  }
}
