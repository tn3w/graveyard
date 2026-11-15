import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:youtube_music_unbound/main.dart';

void main() {
  testWidgets('App initializes without errors', (WidgetTester tester) async {
    await tester.pumpWidget(const YouTubeMusicUnbound());

    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
