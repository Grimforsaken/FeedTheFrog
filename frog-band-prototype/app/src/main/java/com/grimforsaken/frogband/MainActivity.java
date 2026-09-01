package com.grimforsaken.frogband;

import android.app.Activity;
import android.os.Bundle;
import android.os.SystemClock;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Typeface;
import android.media.AudioManager;
import android.media.ToneGenerator;
import android.view.MotionEvent;
import android.view.View;
import android.content.Context;
import java.util.ArrayList;
import java.util.Comparator;

public class MainActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(new GameView(this));
    }

    static final class Note {
        final int lane;
        final long timeMs;
        boolean judged;
        String result = "";
        Note(int lane, long timeMs) { this.lane = lane; this.timeMs = timeMs; }
    }

    static final class Frog {
        int perfectStreak;
        int missStreak;
        int state; // 0 normal, 1 blue shock, 2 on fire
        long playUntil;
    }

    static final class GameView extends View {
        final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        final Paint line = new Paint(Paint.ANTI_ALIAS_FLAG);
        final ArrayList<Note> notes = new ArrayList<>();
        final Frog[] frogs = { new Frog(), new Frog(), new Frog(), new Frog() };
        final String[] names = { "GUITAR", "BASS", "DRUMS", "KEYBOARD" };
        final int[] laneColor = {
            Color.rgb(242, 82, 82), Color.rgb(77, 166, 235),
            Color.rgb(247, 200, 62), Color.rgb(170, 105, 235)
        };
        final ToneGenerator[] tones = new ToneGenerator[4];

        long songStart;
        long previousSongTime;
        int score;
        int combo;
        int bestCombo;
        String feedback = "GET READY";
        long feedbackUntil;
        boolean finished;

        static final long TRAVEL = 1800;
        static final long PERFECT = 45;
        static final long GREAT = 90;
        static final long GOOD = 140;
        static final long END_TIME = 35000;

        GameView(Context context) {
            super(context);
            setKeepScreenOn(true);
            line.setStyle(Paint.Style.STROKE);
            line.setStrokeCap(Paint.Cap.ROUND);
            tones[0] = new ToneGenerator(AudioManager.STREAM_MUSIC, 45);
            tones[1] = new ToneGenerator(AudioManager.STREAM_MUSIC, 45);
            tones[2] = new ToneGenerator(AudioManager.STREAM_MUSIC, 55);
            tones[3] = new ToneGenerator(AudioManager.STREAM_MUSIC, 45);
            buildChart();
            restart();
        }

        void buildChart() {
            notes.clear();
            long first = 2600;
            long beat = 500;
            for (int i = 0; i < 64; i++) {
                long t = first + i * beat;
                notes.add(new Note(2, t));
                if (i % 2 == 0 || i % 8 == 7) notes.add(new Note(1, t));
                if (i % 2 == 0) notes.add(new Note(0, t));
                if (i % 8 == 3 || i % 8 == 7) notes.add(new Note(0, t + 250));
                if (i % 4 == 1 || i % 4 == 3) notes.add(new Note(3, t));
            }
            notes.sort(Comparator.comparingLong(n -> n.timeMs));
        }

        void restart() {
            for (Note n : notes) { n.judged = false; n.result = ""; }
            for (Frog f : frogs) {
                f.perfectStreak = 0; f.missStreak = 0; f.state = 0; f.playUntil = 0;
            }
            score = 0; combo = 0; bestCombo = 0; finished = false;
            feedback = "GET READY"; feedbackUntil = 0;
            songStart = SystemClock.elapsedRealtime();
            previousSongTime = 0;
            invalidate();
        }

        @Override protected void onDraw(Canvas c) {
            long now = SystemClock.elapsedRealtime();
            long song = now - songStart;
            update(song, now);
            drawStage(c);
            drawHeader(c, song);
            drawFrogs(c, now);
            drawLanes(c, song);
            drawFeedback(c, now);
            if (finished) drawFinish(c);
            previousSongTime = song;
            postInvalidateOnAnimation();
        }

        void update(long song, long now) {
            if (finished) return;
            for (Note n : notes) {
                if (previousSongTime < n.timeMs && song >= n.timeMs) {
                    frogs[n.lane].playUntil = now + 170;
                    playTone(n.lane);
                }
                if (!n.judged && song > n.timeMs + GOOD) {
                    n.judged = true;
                    n.result = "MISS";
                    applyResult(n.lane, "MISS", now);
                }
            }
            if (song > END_TIME) {
                finished = true;
                feedback = "SONG COMPLETE";
            }
        }

        void playTone(int lane) {
            int tone;
            if (lane == 0) tone = ToneGenerator.TONE_DTMF_9;
            else if (lane == 1) tone = ToneGenerator.TONE_DTMF_2;
            else if (lane == 2) tone = ToneGenerator.TONE_PROP_BEEP2;
            else tone = ToneGenerator.TONE_DTMF_6;
            tones[lane].startTone(tone, 65);
        }

        void hitLane(int lane, long song, long now) {
            if (finished) { restart(); return; }
            Note best = null;
            long bestDiff = Long.MAX_VALUE;
            for (Note n : notes) {
                if (n.lane != lane || n.judged) continue;
                long d = Math.abs(song - n.timeMs);
                if (d < bestDiff) { best = n; bestDiff = d; }
                if (n.timeMs > song + GOOD) break;
            }
            if (best == null || bestDiff > GOOD) {
                feedback = "TOO EARLY / LATE";
                feedbackUntil = now + 350;
                return;
            }
            String result = bestDiff <= PERFECT ? "PERFECT" : bestDiff <= GREAT ? "GREAT" : "GOOD";
            best.judged = true;
            best.result = result;
            frogs[lane].playUntil = now + 170;
            applyResult(lane, result, now);
        }

        void applyResult(int lane, String result, long now) {
            Frog f = frogs[lane];
            if ("PERFECT".equals(result)) {
                f.missStreak = 0;
                f.perfectStreak++;
                combo++;
                score += 1000 + Math.min(combo, 50) * 10;
                f.state = f.perfectStreak >= 5 ? 2 : 0;
            } else if ("GREAT".equals(result)) {
                f.missStreak = 0; f.perfectStreak = 0; f.state = 0;
                combo++; score += 650 + Math.min(combo, 50) * 5;
            } else if ("GOOD".equals(result)) {
                f.missStreak = 0; f.perfectStreak = 0; f.state = 0;
                combo++; score += 350;
            } else {
                f.perfectStreak = 0;
                f.missStreak++;
                combo = 0;
                f.state = f.missStreak >= 3 ? 1 : 0;
            }
            bestCombo = Math.max(bestCombo, combo);
            feedback = result;
            if (f.state == 1) feedback += "  •  BLUE SHOCK!";
            if (f.state == 2) feedback += "  •  ON FIRE!";
            feedbackUntil = now + 520;
        }

        void drawStage(Canvas c) {
            c.drawColor(Color.rgb(8, 20, 13));
            p.setColor(Color.rgb(18, 43, 28));
            c.drawRect(0, 0, getWidth(), d(245), p);
        }

        void drawHeader(Canvas c, long song) {
            text(c, "FROG BAND", getWidth()/2f, d(30), d(27), Color.WHITE, true);
            text(c, "SCORE " + score + "     COMBO x" + combo + "     BEST " + bestCombo,
                    getWidth()/2f, d(54), d(12), Color.rgb(225,235,225), true);
            float left = d(18), right = getWidth() - d(18), y = d(67);
            p.setColor(Color.rgb(45, 72, 52));
            c.drawRoundRect(left, y, right, y+d(8), d(4), d(4), p);
            float progress = Math.max(0f, Math.min(1f, song/(float)END_TIME));
            p.setColor(Color.rgb(113, 221, 126));
            c.drawRoundRect(left, y, left+(right-left)*progress, y+d(8), d(4), d(4), p);
        }

        void drawFrogs(Canvas c, long now) {
            float laneW = getWidth()/4f;
            for (int i=0;i<4;i++) {
                float x = laneW*(i+.5f);
                drawFrog(c, i, x, d(145), now);
                text(c, names[i], x, d(224), d(10), Color.WHITE, true);
            }
        }

        void drawFrog(Canvas c, int lane, float x, float y, long now) {
            Frog f = frogs[lane];
            boolean playing = now < f.playUntil;
            float bob = playing ? d(4) : 0;
            y -= bob;

            if (f.state == 2) drawFire(c, x, y);
            if (f.state == 1) drawShock(c, x, y);

            int green = f.state == 1 ? Color.rgb(74,151,219) : Color.rgb(87,181,76);
            p.setColor(green);
            c.drawOval(x-d(27), y-d(20), x+d(27), y+d(30), p);
            c.drawCircle(x-d(16), y-d(25), d(12), p);
            c.drawCircle(x+d(16), y-d(25), d(12), p);
            p.setColor(Color.WHITE);
            c.drawCircle(x-d(16), y-d(26), d(6), p);
            c.drawCircle(x+d(16), y-d(26), d(6), p);
            p.setColor(Color.BLACK);
            c.drawCircle(x-d(16), y-d(26), d(2.5f), p);
            c.drawCircle(x+d(16), y-d(26), d(2.5f), p);

            line.setStrokeWidth(d(3));
            line.setColor(Color.rgb(28,67,30));
            c.drawArc(x-d(12),y-d(5),x+d(12),y+d(11),0,180,false,line);
            drawInstrument(c, lane, x, y, playing);
        }

        void drawInstrument(Canvas c, int lane, float x, float y, boolean playing) {
            float m = playing ? d(7) : 0;
            line.setStrokeCap(Paint.Cap.ROUND);
            if (lane == 0) {
                p.setColor(Color.rgb(210,62,58));
                c.drawOval(x-d(5),y+d(6),x+d(29),y+d(27),p);
                line.setStrokeWidth(d(5)); line.setColor(Color.rgb(230,205,150));
                c.drawLine(x+d(14),y+d(12),x-d(35),y-d(14),line);
                line.setStrokeWidth(d(3)); line.setColor(Color.WHITE);
                c.drawLine(x-d(4),y-m,x+d(22),y+d(21)+m,line);
            } else if (lane == 1) {
                p.setColor(Color.rgb(50,105,192));
                c.drawOval(x-d(7),y+d(7),x+d(28),y+d(27),p);
                line.setStrokeWidth(d(5)); line.setColor(Color.rgb(230,205,150));
                c.drawLine(x+d(13),y+d(13),x-d(37),y-d(10),line);
                line.setStrokeWidth(d(2)); line.setColor(Color.WHITE);
                c.drawLine(x+d(3),y+d(12),x+d(25),y+d(20)+m,line);
            } else if (lane == 2) {
                p.setColor(Color.rgb(175,55,55));
                c.drawCircle(x-d(16),y+d(22),d(14),p);
                c.drawCircle(x+d(16),y+d(22),d(14),p);
                line.setStrokeWidth(d(3)); line.setColor(Color.rgb(224,186,115));
                c.drawLine(x-d(18),y-d(2)-m,x-d(6),y+d(20),line);
                c.drawLine(x+d(18),y-d(2)-m,x+d(6),y+d(20),line);
                p.setColor(Color.rgb(225,194,67));
                c.drawOval(x-d(38),y-d(7),x-d(6),y,p);
                c.drawOval(x+d(6),y-d(7),x+d(38),y,p);
            } else {
                p.setColor(Color.rgb(38,38,48));
                c.drawRoundRect(x-d(38),y+d(8),x+d(38),y+d(30),d(3),d(3),p);
                p.setColor(Color.WHITE);
                for(int k=0;k<8;k++) c.drawRect(x-d(34)+k*d(8.5f),y+d(11),x-d(28)+k*d(8.5f),y+d(27),p);
                line.setStrokeWidth(d(4)); line.setColor(Color.rgb(87,181,76));
                c.drawLine(x-d(14),y-m,x-d(10),y+d(17),line);
                c.drawLine(x+d(14),y-m,x+d(10),y+d(17),line);
            }
        }

        void drawFire(Canvas c, float x, float y) {
            p.setColor(Color.rgb(255,91,25));
            for (int i=0;i<7;i++) {
                double a=i*Math.PI*2/7.0;
                float fx=x+(float)Math.cos(a)*d(35), fy=y+(float)Math.sin(a)*d(35);
                Path flame=new Path();
                flame.moveTo(fx-d(6),fy+d(11));
                flame.lineTo(fx,fy-d(17)-(i%3)*d(4));
                flame.lineTo(fx+d(6),fy+d(11));
                flame.close(); c.drawPath(flame,p);
            }
            p.setColor(Color.argb(90,255,214,52)); c.drawCircle(x,y,d(39),p);
        }

        void drawShock(Canvas c, float x, float y) {
            p.setColor(Color.argb(120,70,175,255)); c.drawCircle(x,y,d(43),p);
            line.setColor(Color.rgb(172,232,255)); line.setStrokeWidth(d(3));
            for(int i=0;i<4;i++) {
                float sx=x-d(38)+i*d(24);
                Path z=new Path(); z.moveTo(sx,y-d(40));z.lineTo(sx+d(9),y-d(25));z.lineTo(sx+d(3),y-d(10));z.lineTo(sx+d(13),y+d(2));
                c.drawPath(z,line);
            }
        }

        void drawLanes(Canvas c, long song) {
            float top=d(245), bottom=getHeight()-d(92), hit=bottom-d(25), laneW=getWidth()/4f;
            for(int i=0;i<4;i++) {
                p.setColor(Color.argb(35,255,255,255));
                c.drawRect(i*laneW+d(2),top,(i+1)*laneW-d(2),bottom,p);
                p.setColor(laneColor[i]);
                c.drawRect(i*laneW+d(4),hit,(i+1)*laneW-d(4),hit+d(5),p);
                text(c,names[i],laneW*(i+.5f),bottom+d(20),d(10),Color.WHITE,true);
            }
            for(Note n:notes) {
                long dt=n.timeMs-song;
                if(dt>TRAVEL || dt<-320) continue;
                float y=top+(1f-dt/(float)TRAVEL)*(hit-top);
                float x=laneW*(n.lane+.5f);
                p.setColor(n.judged ? Color.rgb(75,75,75) : laneColor[n.lane]);
                c.drawCircle(x,y,d(14),p);
                if(n.judged && !n.result.isEmpty()) text(c,n.result,x,y+d(3),d(8),Color.WHITE,true);
            }
        }

        void drawFeedback(Canvas c, long now) {
            if (now > feedbackUntil && !"GET READY".equals(feedback)) return;
            text(c,feedback,getWidth()/2f,getHeight()-d(48),d(16),Color.WHITE,true);
            text(c,"Tap a lane when its note reaches the colored line",getWidth()/2f,getHeight()-d(25),d(9),Color.rgb(190,211,195),false);
        }

        void drawFinish(Canvas c) {
            p.setColor(Color.argb(220,0,0,0)); c.drawRect(0,0,getWidth(),getHeight(),p);
            text(c,"SONG COMPLETE",getWidth()/2f,getHeight()/2f-d(28),d(29),Color.WHITE,true);
            text(c,"Score " + score + "   •   Best Combo " + bestCombo,getWidth()/2f,getHeight()/2f+d(6),d(16),Color.WHITE,true);
            text(c,"Tap anywhere to play again",getWidth()/2f,getHeight()/2f+d(43),d(13),Color.rgb(177,235,184),true);
        }

        void text(Canvas c, String s, float x, float y, float size, int color, boolean bold) {
            p.setTextAlign(Paint.Align.CENTER); p.setTextSize(size); p.setColor(color);
            p.setTypeface(bold ? Typeface.DEFAULT_BOLD : Typeface.DEFAULT);
            c.drawText(s,x,y,p);
        }

        float d(float v) { return v*getResources().getDisplayMetrics().density; }

        @Override public boolean onTouchEvent(MotionEvent e) {
            int a=e.getActionMasked();
            if(a==MotionEvent.ACTION_DOWN || a==MotionEvent.ACTION_POINTER_DOWN) {
                int index=e.getActionIndex();
                int lane=Math.max(0,Math.min(3,(int)(e.getX(index)/(getWidth()/4f))));
                long now=SystemClock.elapsedRealtime();
                hitLane(lane,now-songStart,now);
                invalidate();
            }
            return true;
        }

        @Override protected void onDetachedFromWindow() {
            super.onDetachedFromWindow();
            for(ToneGenerator t:tones) if(t!=null) t.release();
        }
    }
}
