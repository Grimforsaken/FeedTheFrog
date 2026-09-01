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
        Note(int lane, long timeMs) { this.lane = lane; this.timeMs = timeMs; }
    }

    static final class Frog {
        int perfectStreak;
        int missStreak;
        int state; // 0 normal, 1 shocked, 2 on fire
        long playUntil;
    }

    static final class GameView extends View {
        final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        final Paint stroke = new Paint(Paint.ANTI_ALIAS_FLAG);
        final ArrayList<Note> notes = new ArrayList<>();
        final Frog[] frogs = { new Frog(), new Frog(), new Frog(), new Frog() };
        final String[] names = { "GUITAR", "BASS", "DRUMS", "KEYBOARD" };
        final String[] roles = { "Electric Guitar", "Bass Guitar", "Drum Kit", "Keyboard" };
        final int[] laneColor = {
                Color.rgb(230,75,75), Color.rgb(72,153,225),
                Color.rgb(238,187,49), Color.rgb(160,96,222)
        };
        final ToneGenerator[] tones = new ToneGenerator[4];

        static final long TRAVEL = 1800;
        static final long PERFECT = 45;
        static final long GREAT = 90;
        static final long GOOD = 140;
        static final long END_TIME = 35000;

        int selectedLane = -1;
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
            stroke.setStyle(Paint.Style.STROKE);
            stroke.setStrokeCap(Paint.Cap.ROUND);
            tones[0] = new ToneGenerator(AudioManager.STREAM_MUSIC, 42);
            tones[1] = new ToneGenerator(AudioManager.STREAM_MUSIC, 42);
            tones[2] = new ToneGenerator(AudioManager.STREAM_MUSIC, 55);
            tones[3] = new ToneGenerator(AudioManager.STREAM_MUSIC, 42);
            buildChart();
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

        void startSong(int lane) {
            selectedLane = lane;
            choosing = false;
            finished = false;
            score = 0;
            combo = 0;
            bestCombo = 0;
            feedback = "GET READY — PLAY " + names[lane];
            feedbackUntil = SystemClock.elapsedRealtime() + 1600;
            for (Note n : notes) n.judged = false;
            for (Frog f : frogs) {
                f.perfectStreak = 0;
                f.missStreak = 0;
                f.state = 0;
                f.playUntil = 0;
            }
            songStart = SystemClock.elapsedRealtime();
            previousSongTime = 0;
            invalidate();
        }

        void returnToChooser() {
            choosing = true;
            finished = false;
            selectedLane = -1;
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
                    playTone(n.lane);
                    if (n.lane != selectedLane) frogs[n.lane].playUntil = now + 170;
                }
                if (n.lane == selectedLane && !n.judged && song > n.timeMs + GOOD) {
                    n.judged = true;
                    applyResult("MISS", now);
                }
                if (n.lane != selectedLane && song > n.timeMs + GOOD) n.judged = true;
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

        void hitSelectedLane(long song, long now) {
            if (finished) {
                returnToChooser();
                return;
            }
            Note best = null;
            long bestDiff = Long.MAX_VALUE;
            for (Note n : notes) {
                if (n.lane != selectedLane || n.judged) continue;
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
            best.judged = true;
            frogs[selectedLane].playUntil = now + 180;
            String result = bestDiff <= PERFECT ? "PERFECT" : bestDiff <= GREAT ? "GREAT" : "GOOD";
            applyResult(result, now);
        }

        void applyResult(String result, long now) {
            Frog f = frogs[selectedLane];
            if ("PERFECT".equals(result)) {
                f.missStreak = 0;
                f.perfectStreak++;
                combo++;
                score += 1000 + Math.min(combo, 50) * 10;
                f.state = f.perfectStreak >= 5 ? 2 : 0;
            } else if ("GREAT".equals(result)) {
                f.missStreak = 0;
                f.perfectStreak = 0;
                f.state = 0;
                combo++;
                score += 650 + Math.min(combo, 50) * 5;
            } else if ("GOOD".equals(result)) {
                f.missStreak = 0;
                f.perfectStreak = 0;
                f.state = 0;
                combo++;
                score += 350;
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
            feedbackUntil = now + 560;
        }

        void drawChooser(Canvas c) {
            c.drawColor(Color.rgb(7, 17, 11));
            text(c, "FROG BAND", getWidth()/2f, d(58), d(34), Color.WHITE, true);
            text(c, "CHOOSE YOUR FROG", getWidth()/2f, d(94), d(18), Color.rgb(160,236,159), true);
            text(c, "Tap one musician to play their part", getWidth()/2f, d(119), d(12), Color.rgb(210,222,212), true);

            float left = d(22);
            float right = getWidth() - d(22);
            float gap = d(12);
            float top = d(150);
            float cardH = (getHeight() - top - d(32) - gap * 3) / 4f;
            for (int i = 0; i < 4; i++) {
                float y1 = top + i * (cardH + gap);
                float y2 = y1 + cardH;
                p.setColor(Color.rgb(18, 43, 28));
                c.drawRoundRect(left, y1, right, y2, d(15), d(15), p);
                p.setColor(laneColor[i]);
                c.drawRoundRect(left, y1, left + d(8), y2, d(8), d(8), p);
                float frogX = left + d(58);
                float frogY = (y1 + y2)/2f;
                drawChoiceFrog(c, i, frogX, frogY);
                textLeft(c, names[i], left + d(112), frogY - d(7), d(20), Color.WHITE);
                textLeft(c, roles[i], left + d(112), frogY + d(17), d(12), Color.rgb(188,211,191));
                text(c, "PLAY", right-d(32), frogY+d(5), d(11), laneColor[i], true);
            }
        }

        void drawChoiceFrog(Canvas c, int lane, float x, float y) {
            p.setColor(Color.rgb(87,181,76));
            c.drawOval(x-d(24), y-d(18), x+d(24), y+d(25), p);
            c.drawCircle(x-d(14), y-d(22), d(10), p);
            c.drawCircle(x+d(14), y-d(22), d(10), p);
            p.setColor(Color.WHITE);
            c.drawCircle(x-d(14), y-d(23), d(5), p);
            c.drawCircle(x+d(14), y-d(23), d(5), p);
            p.setColor(Color.BLACK);
            c.drawCircle(x-d(14), y-d(23), d(2), p);
            c.drawCircle(x+d(14), y-d(23), d(2), p);
            drawInstrument(c, lane, x, y, false);
        }

        void drawStage(Canvas c) {
            c.drawColor(Color.rgb(8,20,13));
            p.setColor(Color.rgb(18,43,28));
            c.drawRect(0,0,getWidth(),d(238),p);
        }

        void drawHeader(Canvas c, long song) {
            text(c,"FROG BAND",getWidth()/2f,d(29),d(25),Color.WHITE,true);
            text(c,"YOU: " + names[selectedLane] + "     SCORE " + score + "     COMBO x" + combo,
                    getWidth()/2f,d(53),d(11),Color.rgb(225,235,225),true);
            float left=d(18),right=getWidth()-d(18),y=d(66);
            p.setColor(Color.rgb(45,72,52));
            c.drawRoundRect(left,y,right,y+d(7),d(4),d(4),p);
            float progress=Math.max(0f,Math.min(1f,song/(float)END_TIME));
            p.setColor(Color.rgb(113,221,126));
            c.drawRoundRect(left,y,left+(right-left)*progress,y+d(7),d(4),d(4),p);
        }

        void drawFrogs(Canvas c, long now) {
            float laneW=getWidth()/4f;
            for(int i=0;i<4;i++) {
                float x=laneW*(i+.5f);
                if(i==selectedLane) {
                    p.setColor(Color.argb(55,255,255,255));
                    c.drawRoundRect(i*laneW+d(3),d(83),(i+1)*laneW-d(3),d(230),d(10),d(10),p);
                    text(c,"YOU",x,d(98),d(9),laneColor[i],true);
                } else {
                    text(c,"AUTO",x,d(98),d(8),Color.rgb(150,170,155),true);
                }
                drawFrog(c,i,x,d(155),now);
                text(c,names[i],x,d(224),d(9),Color.WHITE,true);
            }
        }

        void drawFrog(Canvas c,int lane,float x,float y,long now) {
            Frog f=frogs[lane];
            boolean playing=now<f.playUntil;
            y -= playing ? d(4) : 0;
            if(f.state==2) drawFire(c,x,y);
            if(f.state==1) drawShock(c,x,y);
            int green=f.state==1 ? Color.rgb(74,151,219) : Color.rgb(87,181,76);
            p.setColor(green);
            c.drawOval(x-d(27),y-d(20),x+d(27),y+d(30),p);
            c.drawCircle(x-d(16),y-d(25),d(12),p);
            c.drawCircle(x+d(16),y-d(25),d(12),p);
            p.setColor(Color.WHITE);
            c.drawCircle(x-d(16),y-d(26),d(6),p);
            c.drawCircle(x+d(16),y-d(26),d(6),p);
            p.setColor(Color.BLACK);
            c.drawCircle(x-d(16),y-d(26),d(2.5f),p);
            c.drawCircle(x+d(16),y-d(26),d(2.5f),p);
            stroke.setStrokeWidth(d(3));
            stroke.setColor(Color.rgb(28,67,30));
            c.drawArc(x-d(12),y-d(5),x+d(12),y+d(11),0,180,false,stroke);
            drawInstrument(c,lane,x,y,playing);
        }

        void drawInstrument(Canvas c,int lane,float x,float y,boolean playing) {
            float m=playing?d(7):0;
            if(lane==0) {
                p.setColor(Color.rgb(210,62,58));
                c.drawOval(x-d(5),y+d(6),x+d(29),y+d(27),p);
                stroke.setStrokeWidth(d(5)); stroke.setColor(Color.rgb(230,205,150));
                c.drawLine(x+d(14),y+d(12),x-d(35),y-d(14),stroke);
                stroke.setStrokeWidth(d(3)); stroke.setColor(Color.WHITE);
                c.drawLine(x-d(4),y-m,x+d(22),y+d(21)+m,stroke);
            } else if(lane==1) {
                p.setColor(Color.rgb(50,105,192));
                c.drawOval(x-d(7),y+d(7),x+d(28),y+d(27),p);
                stroke.setStrokeWidth(d(5)); stroke.setColor(Color.rgb(230,205,150));
                c.drawLine(x+d(13),y+d(13),x-d(37),y-d(10),stroke);
                stroke.setStrokeWidth(d(2)); stroke.setColor(Color.WHITE);
                c.drawLine(x+d(3),y+d(12),x+d(25),y+d(20)+m,stroke);
            } else if(lane==2) {
                p.setColor(Color.rgb(175,55,55));
                c.drawCircle(x-d(16),y+d(22),d(14),p);
                c.drawCircle(x+d(16),y+d(22),d(14),p);
                stroke.setStrokeWidth(d(3)); stroke.setColor(Color.rgb(224,186,115));
                c.drawLine(x-d(18),y-d(2)-m,x-d(6),y+d(20),stroke);
                c.drawLine(x+d(18),y-d(2)-m,x+d(6),y+d(20),stroke);
                p.setColor(Color.rgb(225,194,67));
                c.drawOval(x-d(38),y-d(7),x-d(6),y,p);
                c.drawOval(x+d(6),y-d(7),x+d(38),y,p);
            } else {
                p.setColor(Color.rgb(38,38,48));
                c.drawRoundRect(x-d(38),y+d(8),x+d(38),y+d(30),d(3),d(3),p);
                p.setColor(Color.WHITE);
                for(int k=0;k<8;k++) c.drawRect(x-d(34)+k*d(8.5f),y+d(11),x-d(28)+k*d(8.5f),y+d(27),p);
                stroke.setStrokeWidth(d(4)); stroke.setColor(Color.rgb(87,181,76));
                c.drawLine(x-d(14),y-m,x-d(10),y+d(17),stroke);
                c.drawLine(x+d(14),y-m,x+d(10),y+d(17),stroke);
            }
        }

        void drawFire(Canvas c,float x,float y) {
            p.setColor(Color.rgb(255,91,25));
            for(int i=0;i<7;i++) {
                double a=i*Math.PI*2/7.0;
                float fx=x+(float)Math.cos(a)*d(35),fy=y+(float)Math.sin(a)*d(35);
                Path flame=new Path();
                flame.moveTo(fx-d(6),fy+d(11));
                flame.lineTo(fx,fy-d(17)-(i%3)*d(4));
                flame.lineTo(fx+d(6),fy+d(11));
                flame.close();
                c.drawPath(flame,p);
            }
            p.setColor(Color.argb(90,255,214,52));
            c.drawCircle(x,y,d(39),p);
        }

        void drawShock(Canvas c,float x,float y) {
            p.setColor(Color.argb(120,70,175,255));
            c.drawCircle(x,y,d(43),p);
            stroke.setColor(Color.rgb(172,232,255));
            stroke.setStrokeWidth(d(3));
            for(int i=0;i<4;i++) {
                float sx=x-d(38)+i*d(24);
                Path z=new Path();
                z.moveTo(sx,y-d(40));
                z.lineTo(sx+d(9),y-d(25));
                z.lineTo(sx+d(3),y-d(10));
                z.lineTo(sx+d(13),y+d(2));
                c.drawPath(z,stroke);
            }
        }

        void drawLanes(Canvas c,long song) {
            float laneW=getWidth()/4f;
            float top=d(238);
            float hitY=getHeight()*0.75f;
            float bottom=getHeight();

            for(int i=0;i<4;i++) {
                if(i==selectedLane) p.setColor(Color.argb(42,255,255,255));
                else p.setColor(Color.argb(14,255,255,255));
                c.drawRect(i*laneW+d(2),top,(i+1)*laneW-d(2),bottom,p);
            }

            p.setColor(Color.WHITE);
            c.drawRect(0,hitY-d(2),getWidth(),hitY+d(2),p);
            p.setColor(laneColor[selectedLane]);
            c.drawRect(selectedLane*laneW,hitY-d(6),(selectedLane+1)*laneW,hitY+d(6),p);
            text(c,"TAP",laneW*(selectedLane+.5f),hitY+d(27),d(11),Color.WHITE,true);

            for(Note n:notes) {
                long delta=n.timeMs-song;
                if(delta>TRAVEL || delta<-GOOD) continue;
                if(n.judged && n.lane==selectedLane) continue;
                float t=1f-(delta/(float)TRAVEL);
                float y=top+(hitY-top)*t;
                float x=laneW*(n.lane+.5f);
                if(n.lane==selectedLane) {
                    p.setColor(laneColor[n.lane]);
                    c.drawCircle(x,y,d(14),p);
                    p.setColor(Color.WHITE);
                    c.drawCircle(x,y,d(5),p);
                } else {
                    int base=laneColor[n.lane];
                    p.setColor(Color.argb(90,Color.red(base),Color.green(base),Color.blue(base)));
                    c.drawCircle(x,y,d(8),p);
                }
            }
        }

        void drawFeedback(Canvas c,long now) {
            if(feedback.length()==0) return;
            if(now>feedbackUntil && !finished) return;
            int color=Color.WHITE;
            if(feedback.startsWith("PERFECT")) color=Color.rgb(255,221,74);
            else if(feedback.startsWith("GREAT")) color=Color.rgb(116,221,255);
            else if(feedback.startsWith("GOOD")) color=Color.rgb(149,232,132);
            else if(feedback.startsWith("MISS")) color=Color.rgb(255,103,103);
            text(c,feedback,getWidth()/2f,getHeight()*0.66f,d(18),color,true);
        }

        void drawFinish(Canvas c) {
            p.setColor(Color.argb(220,5,12,8));
            c.drawRoundRect(d(28),getHeight()/2f-d(92),getWidth()-d(28),getHeight()/2f+d(92),d(18),d(18),p);
            text(c,"SONG COMPLETE",getWidth()/2f,getHeight()/2f-d(44),d(24),Color.WHITE,true);
            text(c,"Score " + score + "   •   Best Combo " + bestCombo,getWidth()/2f,getHeight()/2f-d(8),d(13),Color.rgb(209,230,211),true);
            text(c,"Tap to pick a different frog",getWidth()/2f,getHeight()/2f+d(35),d(13),Color.rgb(160,236,159),true);
        }

        @Override public boolean onTouchEvent(MotionEvent e) {
            if(e.getAction()!=MotionEvent.ACTION_DOWN) return true;
            if(choosing) {
                float gap=d(12);
                float top=d(150);
                float cardH=(getHeight()-top-d(32)-gap*3)/4f;
                for(int i=0;i<4;i++) {
                    float y1=top+i*(cardH+gap);
                    float y2=y1+cardH;
                    if(e.getY()>=y1 && e.getY()<=y2) {
                        startSong(i);
                        return true;
                    }
                }
                return true;
            }
            if(finished) {
                returnToChooser();
                return true;
            }
            float laneW=getWidth()/4f;
            int tapped=(int)(e.getX()/laneW);
            if(tapped==selectedLane) {
                long now=SystemClock.elapsedRealtime();
                hitSelectedLane(now-songStart,now);
            }
            return true;
        }

        float d(float value) { return value*getResources().getDisplayMetrics().density; }

        void text(Canvas c,String s,float x,float y,float size,int color,boolean center) {
            p.setTypeface(Typeface.create(Typeface.DEFAULT,Typeface.BOLD));
            p.setTextSize(size);
            p.setColor(color);
            p.setTextAlign(center?Paint.Align.CENTER:Paint.Align.LEFT);
            c.drawText(s,x,y,p);
        }

        void textLeft(Canvas c,String s,float x,float y,float size,int color) {
            text(c,s,x,y,size,color,false);
        }
    }
}