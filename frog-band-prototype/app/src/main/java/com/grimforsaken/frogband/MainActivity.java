package com.grimforsaken.frogband;

import android.app.Activity;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Typeface;
import android.media.AudioManager;
import android.media.ToneGenerator;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.SparseIntArray;
import android.view.MotionEvent;
import android.view.View;

import java.util.ArrayList;
import java.util.Comparator;

public class MainActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(new GameView(this));
    }

    static final class Note {
        final int side;          // 0 = left thumb, 1 = right thumb
        final long timeMs;
        final long durationMs;   // 0 = tap, >0 = hold
        boolean judged;
        boolean holding;
        String holdQuality = "";

        Note(int side, long timeMs, long durationMs) {
            this.side = side;
            this.timeMs = timeMs;
            this.durationMs = durationMs;
        }

        boolean isHold() { return durationMs > 0; }
    }

    static final class Frog {
        int perfectStreak;
        int missStreak;
        int state; // 0 normal, 1 shocked, 2 on fire
        long playUntil;
        int lastSide;
    }

    static final class GameView extends View {
        final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        final Paint stroke = new Paint(Paint.ANTI_ALIAS_FLAG);
        final ArrayList<Note> notes = new ArrayList<>();
        final Frog frog = new Frog();
        final SparseIntArray pointerSides = new SparseIntArray();
        final Note[] activeHold = new Note[2];
        final boolean[] thumbDown = new boolean[2];

        final String[] names = { "GUITAR", "BASS", "DRUMS", "KEYBOARD" };
        final String[] roles = { "Electric Guitar", "Bass Guitar", "Drum Kit", "Keyboard" };
        final int[] instrumentColor = {
                Color.rgb(230,75,75), Color.rgb(72,153,225),
                Color.rgb(238,187,49), Color.rgb(160,96,222)
        };
        final ToneGenerator[] tones = new ToneGenerator[4];

        static final long TRAVEL = 1800;
        static final long PERFECT = 45;
        static final long GREAT = 90;
        static final long GOOD = 140;
        static final long END_TIME = 36000;

        int selectedInstrument = -1;
        boolean choosing = true;
        boolean finished;
        long songStart;
        long previousSongTime;
        int score;
        int combo;
        int bestCombo;
        String feedback = "";
        long feedbackUntil;

        GameView(Context context) {
            super(context);
            setKeepScreenOn(true);
            setFocusable(true);
            stroke.setStyle(Paint.Style.STROKE);
            stroke.setStrokeCap(Paint.Cap.ROUND);
            tones[0] = new ToneGenerator(AudioManager.STREAM_MUSIC, 42);
            tones[1] = new ToneGenerator(AudioManager.STREAM_MUSIC, 42);
            tones[2] = new ToneGenerator(AudioManager.STREAM_MUSIC, 55);
            tones[3] = new ToneGenerator(AudioManager.STREAM_MUSIC, 42);
        }

        void buildChart(int instrument) {
            notes.clear();
            long first = 2600;
            long beat = 500;

            for (int i = 0; i < 64; i++) {
                long t = first + i * beat;
                int side;
                long hold = 0;

                if (instrument == 0) { // guitar: alternating strums with sustained chords
                    side = (i % 4 < 2) ? 0 : 1;
                    if (i % 8 == 3 || i % 8 == 7) hold = 700;
                    notes.add(new Note(side, t, hold));
                    if (i % 8 == 5) notes.add(new Note(1 - side, t + 250, 0));
                } else if (instrument == 1) { // bass: steady alternating pulse + long notes
                    side = i % 2;
                    if (i % 8 == 0 || i % 8 == 4) hold = 900;
                    notes.add(new Note(side, t, hold));
                } else if (instrument == 2) { // drums: faster two-thumb pattern, rare sustained roll
                    side = (i % 4 == 0 || i % 4 == 3) ? 0 : 1;
                    notes.add(new Note(side, t, 0));
                    if (i % 4 == 1) notes.add(new Note(1 - side, t + 250, 0));
                    if (i % 16 == 12) notes.add(new Note(1, t + 250, 650));
                } else { // keyboard: alternating melody with sustained notes/chords
                    side = (i % 3 == 0 || i % 3 == 1) ? 0 : 1;
                    if (i % 8 == 2 || i % 8 == 6) hold = 1000;
                    notes.add(new Note(side, t, hold));
                    if (i % 8 == 4) notes.add(new Note(1 - side, t, 0));
                }
            }
            notes.sort(Comparator.comparingLong(n -> n.timeMs));
        }

        void startSong(int instrument) {
            selectedInstrument = instrument;
            choosing = false;
            finished = false;
            score = 0;
            combo = 0;
            bestCombo = 0;
            frog.perfectStreak = 0;
            frog.missStreak = 0;
            frog.state = 0;
            frog.playUntil = 0;
            frog.lastSide = 0;
            pointerSides.clear();
            thumbDown[0] = thumbDown[1] = false;
            activeHold[0] = activeHold[1] = null;
            buildChart(instrument);
            feedback = "GET READY — " + names[instrument];
            feedbackUntil = SystemClock.elapsedRealtime() + 1600;
            songStart = SystemClock.elapsedRealtime();
            previousSongTime = 0;
            invalidate();
        }

        void returnToChooser() {
            choosing = true;
            finished = false;
            selectedInstrument = -1;
            pointerSides.clear();
            thumbDown[0] = thumbDown[1] = false;
            activeHold[0] = activeHold[1] = null;
            feedback = "";
            invalidate();
        }

        @Override protected void onDraw(Canvas c) {
            if (choosing) {
                drawChooser(c);
                return;
            }

            long now = SystemClock.elapsedRealtime();
            long song = now - songStart;
            update(song, now);
            drawGame(c, song, now);
            previousSongTime = song;
            postInvalidateOnAnimation();
        }

        void update(long song, long now) {
            if (finished) return;

            for (Note n : notes) {
                if (previousSongTime < n.timeMs && song >= n.timeMs) {
                    playTone();
                    frog.playUntil = Math.max(frog.playUntil, now + (n.isHold() ? 300 : 170));
                    frog.lastSide = n.side;
                }

                if (n.holding && !n.judged && song >= n.timeMs + n.durationMs) {
                    n.holding = false;
                    n.judged = true;
                    if (activeHold[n.side] == n) activeHold[n.side] = null;
                    score += 250;
                    applyResult(n.holdQuality, now);
                }

                if (!n.judged && !n.holding && song > n.timeMs + GOOD) {
                    n.judged = true;
                    applyResult("MISS", now);
                }
            }

            if (song > END_TIME) {
                finished = true;
                feedback = "SONG COMPLETE";
            }
        }

        void playTone() {
            int tone;
            if (selectedInstrument == 0) tone = ToneGenerator.TONE_DTMF_9;
            else if (selectedInstrument == 1) tone = ToneGenerator.TONE_DTMF_2;
            else if (selectedInstrument == 2) tone = ToneGenerator.TONE_PROP_BEEP2;
            else tone = ToneGenerator.TONE_DTMF_6;
            tones[selectedInstrument].startTone(tone, 65);
        }

        void pressThumb(int side, long song, long now) {
            if (finished) {
                returnToChooser();
                return;
            }
            thumbDown[side] = true;

            Note best = null;
            long bestDiff = Long.MAX_VALUE;
            for (Note n : notes) {
                if (n.side != side || n.judged || n.holding) continue;
                long diff = Math.abs(song - n.timeMs);
                if (diff < bestDiff) {
                    best = n;
                    bestDiff = diff;
                }
                if (n.timeMs > song + GOOD) break;
            }

            if (best == null || bestDiff > GOOD) {
                feedback = "TOO EARLY / LATE";
                feedbackUntil = now + 350;
                return;
            }

            frog.playUntil = now + (best.isHold() ? 320 : 180);
            frog.lastSide = side;
            String quality = bestDiff <= PERFECT ? "PERFECT" : bestDiff <= GREAT ? "GREAT" : "GOOD";

            if (best.isHold()) {
                best.holding = true;
                best.holdQuality = quality;
                activeHold[side] = best;
                feedback = quality + " — HOLD";
                feedbackUntil = now + 450;
            } else {
                best.judged = true;
                applyResult(quality, now);
            }
        }

        void releaseThumb(int side, long song, long now) {
            thumbDown[side] = false;
            Note hold = activeHold[side];
            if (hold == null || hold.judged) return;

            long holdEnd = hold.timeMs + hold.durationMs;
            if (song < holdEnd - 80) {
                hold.holding = false;
                hold.judged = true;
                activeHold[side] = null;
                applyResult("MISS", now);
                feedback = "RELEASED EARLY  •  " + feedback;
                feedbackUntil = now + 650;
            }
        }

        void applyResult(String result, long now) {
            if ("PERFECT".equals(result)) {
                frog.missStreak = 0;
                frog.perfectStreak++;
                combo++;
                score += 1000 + Math.min(combo, 50) * 10;
                frog.state = frog.perfectStreak >= 5 ? 2 : 0;
            } else if ("GREAT".equals(result)) {
                frog.missStreak = 0;
                frog.perfectStreak = 0;
                frog.state = 0;
                combo++;
                score += 650 + Math.min(combo, 50) * 5;
            } else if ("GOOD".equals(result)) {
                frog.missStreak = 0;
                frog.perfectStreak = 0;
                frog.state = 0;
                combo++;
                score += 350;
            } else {
                frog.perfectStreak = 0;
                frog.missStreak++;
                combo = 0;
                frog.state = frog.missStreak >= 3 ? 1 : 0;
            }

            bestCombo = Math.max(bestCombo, combo);
            feedback = result;
            if (frog.state == 1) feedback += "  •  BLUE SHOCK!";
            if (frog.state == 2) feedback += "  •  ON FIRE!";
            feedbackUntil = now + 560;
        }

        void drawChooser(Canvas c) {
            c.drawColor(Color.rgb(7,17,11));
            text(c, "FROG BAND", getWidth()/2f, d(54), d(34), Color.WHITE, true);
            text(c, "PICK YOUR FROG", getWidth()/2f, d(90), d(18), Color.rgb(160,236,159), true);
            text(c, "Only your selected frog appears during the song", getWidth()/2f, d(116), d(11), Color.rgb(205,220,208), true);

            float left = d(20);
            float right = getWidth() - d(20);
            float top = d(142);
            float gap = d(11);
            float cardH = (getHeight() - top - d(24) - gap * 3) / 4f;

            for (int i=0; i<4; i++) {
                float y1 = top + i * (cardH + gap);
                float y2 = y1 + cardH;
                p.setColor(Color.rgb(18,43,28));
                c.drawRoundRect(left,y1,right,y2,d(15),d(15),p);
                p.setColor(instrumentColor[i]);
                c.drawRoundRect(left,y1,left+d(8),y2,d(8),d(8),p);
                float frogX = left + d(58);
                float frogY = (y1+y2)/2f;
                drawSmallFrog(c,i,frogX,frogY);
                textLeft(c,names[i],left+d(112),frogY-d(7),d(20),Color.WHITE);
                textLeft(c,roles[i],left+d(112),frogY+d(17),d(12),Color.rgb(188,211,191));
                text(c,"PLAY",right-d(31),frogY+d(4),d(11),instrumentColor[i],true);
            }
        }

        void drawGame(Canvas c, long song, long now) {
            int w = getWidth();
            int h = getHeight();
            float hitY = h * 0.75f; // exactly 1/4 of the screen up from the bottom
            float leftX = w * 0.28f;
            float rightX = w * 0.72f;
            float spawnY = Math.max(d(250), h * 0.40f);

            c.drawColor(Color.rgb(7,18,12));

            // Header
            text(c,"FROG BAND",w/2f,d(28),d(24),Color.WHITE,true);
            text(c,names[selectedInstrument] + "   SCORE " + score + "   COMBO x" + combo,
                    w/2f,d(52),d(11),Color.rgb(225,235,225),true);
            float barL=d(18), barR=w-d(18), barY=d(64);
            p.setColor(Color.rgb(45,72,52));
            c.drawRoundRect(barL,barY,barR,barY+d(7),d(4),d(4),p);
            p.setColor(Color.rgb(113,221,126));
            float progress = Math.max(0f,Math.min(1f,song/(float)END_TIME));
            c.drawRoundRect(barL,barY,barL+(barR-barL)*progress,barY+d(7),d(4),d(4),p);

            // Single selected frog
            float frogY = Math.min(h * 0.245f, hitY - d(300));
            frogY = Math.max(frogY, d(150));
            drawMainFrog(c, selectedInstrument, w/2f, frogY, now);
            text(c, roles[selectedInstrument], w/2f, frogY+d(88), d(12), Color.rgb(206,224,209), true);

            // Note lanes
            p.setColor(Color.argb(38,255,255,255));
            c.drawRoundRect(d(18),spawnY-d(8),w/2f-d(7),hitY-d(13),d(16),d(16),p);
            c.drawRoundRect(w/2f+d(7),spawnY-d(8),w-d(18),hitY-d(13),d(16),d(16),p);

            for (Note n : notes) {
                if (n.judged) continue;
                long until = n.timeMs - song;
                long endUntil = n.timeMs + n.durationMs - song;
                if (until > TRAVEL || endUntil < -GOOD) continue;
                float x = n.side == 0 ? leftX : rightX;
                float y = hitY - (until / (float)TRAVEL) * (hitY - spawnY);
                y = Math.min(hitY+d(20), y);

                if (!n.isHold()) {
                    p.setColor(instrumentColor[selectedInstrument]);
                    c.drawCircle(x,y,d(18),p);
                    p.setColor(Color.WHITE);
                    c.drawCircle(x,y,d(7),p);
                } else {
                    float endY = hitY - (endUntil / (float)TRAVEL) * (hitY - spawnY);
                    float topY = Math.min(y,endY);
                    float bottomY = Math.max(y,endY);
                    if (n.holding) bottomY = hitY;
                    p.setColor(Color.argb(215,
                            Color.red(instrumentColor[selectedInstrument]),
                            Color.green(instrumentColor[selectedInstrument]),
                            Color.blue(instrumentColor[selectedInstrument])));
                    c.drawRoundRect(x-d(15),topY,x+d(15),bottomY,d(15),d(15),p);
                    p.setColor(Color.WHITE);
                    c.drawCircle(x,y,d(7),p);
                }
            }

            // Hit bar: one quarter of the way up from bottom
            p.setColor(Color.WHITE);
            c.drawRect(0,hitY-d(3),w,hitY+d(3),p);
            text(c,"HIT BAR",w/2f,hitY-d(10),d(9),Color.rgb(205,220,208),true);

            // Two thumb zones below hit bar
            drawThumbZone(c,0,d(12),hitY+d(14),w/2f-d(6),h-d(12),thumbDown[0]);
            drawThumbZone(c,1,w/2f+d(6),hitY+d(14),w-d(12),h-d(12),thumbDown[1]);

            if (now < feedbackUntil || finished) {
                text(c,feedback,w/2f,spawnY-d(23),d(17),Color.WHITE,true);
            }

            if (frog.state == 1) {
                text(c,"3+ MISSES — BLUE SHOCK",w/2f,frogY-d(83),d(12),Color.rgb(120,205,255),true);
            } else if (frog.state == 2) {
                text(c,"5+ PERFECTS — ON FIRE",w/2f,frogY-d(83),d(12),Color.rgb(255,198,83),true);
            }

            if (finished) {
                p.setColor(Color.argb(220,0,0,0));
                c.drawRoundRect(d(24),h*.36f,w-d(24),h*.61f,d(20),d(20),p);
                text(c,"SONG COMPLETE",w/2f,h*.43f,d(27),Color.WHITE,true);
                text(c,"Score " + score + "   Best combo x" + bestCombo,w/2f,h*.49f,d(14),Color.rgb(184,238,188),true);
                text(c,"Tap either thumb zone to choose another frog",w/2f,h*.55f,d(11),Color.LTGRAY,true);
            }
        }

        void drawThumbZone(Canvas c, int side, float l, float t, float r, float b, boolean down) {
            int base = instrumentColor[selectedInstrument];
            int alpha = down ? 170 : 82;
            p.setColor(Color.argb(alpha,Color.red(base),Color.green(base),Color.blue(base)));
            c.drawRoundRect(l,t,r,b,d(22),d(22),p);
            stroke.setStrokeWidth(d(3));
            stroke.setColor(down ? Color.WHITE : Color.argb(180,255,255,255));
            c.drawRoundRect(l,t,r,b,d(22),d(22),stroke);
            float cx=(l+r)/2f;
            float cy=(t+b)/2f;
            text(c,side==0?"LEFT THUMB":"RIGHT THUMB",cx,cy-d(9),d(14),Color.WHITE,true);
            text(c,"TAP  •  HOLD",cx,cy+d(18),d(12),Color.rgb(225,235,225),true);
        }

        void drawSmallFrog(Canvas c,int instrument,float x,float y) {
            p.setColor(Color.rgb(87,181,76));
            c.drawOval(x-d(24),y-d(18),x+d(24),y+d(25),p);
            c.drawCircle(x-d(14),y-d(22),d(10),p);
            c.drawCircle(x+d(14),y-d(22),d(10),p);
            p.setColor(Color.WHITE);
            c.drawCircle(x-d(14),y-d(23),d(5),p);
            c.drawCircle(x+d(14),y-d(23),d(5),p);
            p.setColor(Color.BLACK);
            c.drawCircle(x-d(14),y-d(23),d(2),p);
            c.drawCircle(x+d(14),y-d(23),d(2),p);
            drawInstrument(c,instrument,x,y,false,0);
        }

        void drawMainFrog(Canvas c,int instrument,float x,float y,long now) {
            boolean playing = now < frog.playUntil;
            y -= playing ? d(5) : 0;
            if (frog.state == 2) drawFire(c,x,y);
            if (frog.state == 1) drawShock(c,x,y);

            int green = frog.state == 1 ? Color.rgb(61,139,220) : Color.rgb(87,181,76);
            p.setColor(green);
            c.drawOval(x-d(54),y-d(40),x+d(54),y+d(61),p);
            c.drawCircle(x-d(32),y-d(50),d(23),p);
            c.drawCircle(x+d(32),y-d(50),d(23),p);
            p.setColor(Color.WHITE);
            c.drawCircle(x-d(32),y-d(52),d(11),p);
            c.drawCircle(x+d(32),y-d(52),d(11),p);
            p.setColor(Color.BLACK);
            c.drawCircle(x-d(32),y-d(52),d(4),p);
            c.drawCircle(x+d(32),y-d(52),d(4),p);
            stroke.setStrokeWidth(d(4));
            stroke.setColor(frog.state==1 ? Color.rgb(30,82,145) : Color.rgb(28,67,30));
            c.drawArc(x-d(24),y-d(7),x+d(24),y+d(20),0,180,false,stroke);
            drawInstrument(c,instrument,x,y,playing,frog.lastSide);
        }

        void drawInstrument(Canvas c,int instrument,float x,float y,boolean playing,int side) {
            float m = playing ? d(10) : 0;
            float handShift = side == 0 ? -m : m;
            if (instrument == 0) {
                p.setColor(Color.rgb(210,62,58));
                c.drawOval(x-d(5),y+d(12),x+d(49),y+d(45),p);
                stroke.setStrokeWidth(d(8)); stroke.setColor(Color.rgb(230,205,150));
                c.drawLine(x+d(23),y+d(20),x-d(63),y-d(26),stroke);
                stroke.setStrokeWidth(d(5)); stroke.setColor(Color.WHITE);
                c.drawLine(x-d(5)+handShift,y-m,x+d(37),y+d(38)+m,stroke);
            } else if (instrument == 1) {
                p.setColor(Color.rgb(50,105,192));
                c.drawOval(x-d(9),y+d(13),x+d(48),y+d(45),p);
                stroke.setStrokeWidth(d(8)); stroke.setColor(Color.rgb(230,205,150));
                c.drawLine(x+d(22),y+d(21),x-d(64),y-d(25),stroke);
                stroke.setStrokeWidth(d(5)); stroke.setColor(Color.WHITE);
                c.drawLine(x+d(3)+handShift,y+d(8),x+d(34),y+d(38)+m,stroke);
            } else if (instrument == 2) {
                p.setColor(Color.rgb(205,45,45));
                c.drawCircle(x,y+d(34),d(28),p);
                p.setColor(Color.rgb(235,190,50));
                c.drawOval(x-d(62),y-d(8),x-d(15),y+d(4),p);
                c.drawOval(x+d(15),y-d(8),x+d(62),y+d(4),p);
                stroke.setStrokeWidth(d(5)); stroke.setColor(Color.rgb(225,190,128));
                if (side == 0) c.drawLine(x-d(34),y-d(37)-m,x-d(4),y+d(23),stroke);
                else c.drawLine(x+d(34),y-d(37)-m,x+d(4),y+d(23),stroke);
            } else {
                p.setColor(Color.rgb(70,70,84));
                c.drawRoundRect(x-d(70),y+d(19),x+d(70),y+d(48),d(5),d(5),p);
                p.setColor(Color.WHITE);
                for (int i=0;i<10;i++) {
                    float kx=x-d(62)+i*d(13);
                    c.drawRect(kx,y+d(22),kx+d(9),y+d(43),p);
                }
                stroke.setStrokeWidth(d(7)); stroke.setColor(Color.rgb(118,205,96));
                float hx = side==0 ? x-d(32) : x+d(32);
                c.drawLine(hx,y-m,hx+handShift,y+d(27)+m,stroke);
            }
        }

        void drawFire(Canvas c,float x,float y) {
            for (int i=0;i<7;i++) {
                float fx=x + (i-3)*d(16);
                float top=y-d(84) - (i%2)*d(14);
                Path flame=new Path();
                flame.moveTo(fx-d(10),y+d(54));
                flame.quadTo(fx-d(22),y-d(10),fx,top);
                flame.quadTo(fx+d(25),y-d(7),fx+d(10),y+d(54));
                flame.close();
                p.setColor(i%2==0?Color.rgb(255,111,35):Color.rgb(255,190,45));
                c.drawPath(flame,p);
            }
        }

        void drawShock(Canvas c,float x,float y) {
            stroke.setStrokeWidth(d(5));
            stroke.setColor(Color.rgb(120,215,255));
            for(int i=-2;i<=2;i++) {
                float sx=x+i*d(25);
                Path bolt=new Path();
                bolt.moveTo(sx,y-d(82));
                bolt.lineTo(sx+d(10),y-d(57));
                bolt.lineTo(sx-d(7),y-d(34));
                bolt.lineTo(sx+d(8),y-d(9));
                c.drawPath(bolt,stroke);
            }
        }

        @Override public boolean onTouchEvent(MotionEvent e) {
            int action = e.getActionMasked();
            int index = e.getActionIndex();

            if (choosing) {
                if (action == MotionEvent.ACTION_DOWN) {
                    float y = e.getY();
                    float top = d(142);
                    float gap = d(11);
                    float cardH = (getHeight() - top - d(24) - gap * 3) / 4f;
                    for(int i=0;i<4;i++) {
                        float y1=top+i*(cardH+gap);
                        float y2=y1+cardH;
                        if(y>=y1 && y<=y2) {
                            startSong(i);
                            return true;
                        }
                    }
                }
                return true;
            }

            long now = SystemClock.elapsedRealtime();
            long song = now - songStart;

            if (action == MotionEvent.ACTION_DOWN || action == MotionEvent.ACTION_POINTER_DOWN) {
                int pointerId = e.getPointerId(index);
                int side = e.getX(index) < getWidth()/2f ? 0 : 1;
                pointerSides.put(pointerId, side);
                pressThumb(side, song, now);
                invalidate();
                return true;
            }

            if (action == MotionEvent.ACTION_UP || action == MotionEvent.ACTION_POINTER_UP) {
                int pointerId = e.getPointerId(index);
                int stored = pointerSides.get(pointerId, -1);
                int side = stored >= 0 ? stored : (e.getX(index) < getWidth()/2f ? 0 : 1);
                releaseThumb(side, song, now);
                pointerSides.delete(pointerId);
                invalidate();
                return true;
            }

            if (action == MotionEvent.ACTION_CANCEL) {
                for(int side=0;side<2;side++) {
                    if(thumbDown[side]) releaseThumb(side,song,now);
                }
                pointerSides.clear();
                invalidate();
                return true;
            }

            return true;
        }

        void text(Canvas c,String s,float x,float y,float size,int color,boolean center) {
            p.setColor(color);
            p.setTextSize(size);
            p.setTypeface(Typeface.create(Typeface.DEFAULT,Typeface.BOLD));
            p.setTextAlign(center?Paint.Align.CENTER:Paint.Align.LEFT);
            c.drawText(s,x,y,p);
        }

        void textLeft(Canvas c,String s,float x,float y,float size,int color) {
            text(c,s,x,y,size,color,false);
        }

        float d(float v) { return v * getResources().getDisplayMetrics().density; }
    }
}
