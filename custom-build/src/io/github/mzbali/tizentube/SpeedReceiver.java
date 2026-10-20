package io.github.mzbali.tizentube;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** Accepts only two fixed commands, and only affects our foreground activity. */
public class SpeedReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        if ("io.github.mzbali.tizentube.SLOWER".equals(intent.getAction())) {
            SpeedActivity.adjustForeground(-1);
        } else if ("io.github.mzbali.tizentube.FASTER".equals(intent.getAction())) {
            SpeedActivity.adjustForeground(1);
        }
    }
}
