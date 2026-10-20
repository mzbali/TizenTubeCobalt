package io.github.mzbali.tizentube;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.KeyEvent;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.lang.ref.WeakReference;

/** A small source-built addition to the upstream, precompiled Cobalt engine. */
public class SpeedActivity extends dev.cobalt.app.MainActivity {
    private static WeakReference<SpeedActivity> foreground = new WeakReference<>(null);
    private String speedScript;
    private final Handler startup = new Handler(Looper.getMainLooper());
    private int startupAttempts;
    private final Runnable configure = new Runnable() {
        @Override public void run() {
            if (foreground.get() != SpeedActivity.this || speedScript == null) return;
            evaluateJavaScript(speedScript + "\nwindow.ttInstantSpeed.configureAndroidAddon();");
            if (++startupAttempts < 20) startup.postDelayed(this, 500);
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        try (InputStream stream = getAssets().open("instantSpeed.js")) {
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            byte[] buffer = new byte[4096];
            int count;
            while ((count = stream.read(buffer)) != -1) bytes.write(buffer, 0, count);
            speedScript = bytes.toString("UTF-8");
        } catch (Exception error) {
            Log.e("TTInstantSpeed", "Unable to load bundled speed controls", error);
        }
    }

    @Override protected void onResume() {
        super.onResume();
        foreground = new WeakReference<>(this);
        startupAttempts = 0;
        startup.post(configure);
    }

    @Override protected void onPause() {
        if (foreground.get() == this) foreground.clear();
        startup.removeCallbacks(configure);
        super.onPause();
    }

    static void adjustForeground(int direction) {
        SpeedActivity activity = foreground.get();
        if (activity != null) activity.adjustSpeed(direction);
    }

    private void adjustSpeed(int direction) {
        if (speedScript != null && (direction == -1 || direction == 1)) {
            evaluateJavaScript(speedScript + "\nwindow.ttInstantSpeed.adjust(" + direction + ");");
        }
    }

    @Override public boolean dispatchKeyEvent(KeyEvent event) {
        int key = event.getKeyCode();
        if (key == KeyEvent.KEYCODE_BUTTON_3 || key == KeyEvent.KEYCODE_BUTTON_4) {
            if (event.getAction() == KeyEvent.ACTION_DOWN && event.getRepeatCount() == 0) {
                adjustSpeed(key == KeyEvent.KEYCODE_BUTTON_3 ? -1 : 1);
            }
            return true;
        }
        return super.dispatchKeyEvent(event);
    }
}
