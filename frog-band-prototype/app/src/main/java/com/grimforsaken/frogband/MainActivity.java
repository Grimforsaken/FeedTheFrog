package com.grimforsaken.frogband;

import android.app.Activity;
import android.os.Bundle;
import android.os.SystemClock;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Typeface;
import android.media.MediaPlayer;
import android.view.MotionEvent;
import android.view.View;
import android.content.Context;
import android.util.SparseIntArray;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.ArrayList;

public class MainActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(new GameView(this));
    }

    static final class Note {
        final long timeMs;
        final int lane;
        final long durationMs;
        boolean hit;
        boolean done;
        Note(long t, int l, long d) { timeMs=t; lane=l; durationMs=d; }
    }

    static final class GameView extends View {
        final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        final Paint stroke = new Paint(Paint.ANTI_ALIAS_FLAG);
        final ArrayList<Note> guitar = new ArrayList<>();
        final ArrayList<Note> drums = new ArrayList<>();
        final SparseIntArray pointerLane = new SparseIntArray();
        final int[] lanePointers = new int[4];
        final int[] laneColors = {
                Color.rgb(232,78,78), Color.rgb(247,184,57),
                Color.rgb(75,168,231), Color.rgb(174,103,225)
        };
        final String[] drumLabels = {"KICK","SNARE","HAT","CYM/TOM"};
        final String[] guitarLabels = {"LOW","MID-L","MID-H","HIGH"};

        static final int GUITAR = 0;
        static final int DRUMS = 1;
        static final long TRAVEL_MS = 1900;
        static final long PERFECT_MS = 50;
        static final long GREAT_MS = 95;
        static final long GOOD_MS = 150;
        static final long PREROLL_MS = 2200;
        static final long SONG_MS = 217453;

        boolean choosing = true;
        boolean finished = false;
        boolean audioStarted = false;
        int instrument = GUITAR;
        int score = 0;
        int combo = 0;
        int bestCombo = 0;
        int perfectStreak = 0;
        int missStreak = 0;
        int frogState = 0;
        int lastPlayedLane = 0;
        long frogPlayUntil = 0;
        long songEpoch = 0;
        String feedback = "";
        long feedbackUntil = 0;
        MediaPlayer music;

        GameView(Context context) {
            super(context);
            setKeepScreenOn(true);
            stroke.setStyle(Paint.Style.STROKE);
            stroke.setStrokeCap(Paint.Cap.ROUND);
            loadChart(context, R.raw.guitar_chart, guitar);
            loadChart(context, R.raw.drums_chart, drums);
            music = MediaPlayer.create(context, R.raw.frantic_frog_mix);
            if (music != null) music.setLooping(false);
        }

        void loadChart(Context context, int resource, ArrayList<Note> target) {
            try (BufferedReader br = new BufferedReader(new InputStreamReader(context.getResources().openRawResource(resource)))) {
                String line; boolean first=true;
                while ((line=br.readLine()) != null) {
                    if (first) { first=false; continue; }
                    String[] s=line.trim().split(",");
                    if (s.length < 3) continue;
                    target.add(new Note(Long.parseLong(s[0]), Integer.parseInt(s[1]), Long.parseLong(s[2])));
                }
            } catch (Exception ignored) {}
        }

        ArrayList<Note> chart() { return instrument==GUITAR ? guitar : drums; }

        void startSong(int selected) {
            instrument = selected;
            choosing = false;
            finished = false;
            audioStarted = false;
            score = combo = bestCombo = perfectStreak = missStreak = frogState = 0;
            feedback = "GET READY";
            feedbackUntil = SystemClock.elapsedRealtime() + 1300;
            pointerLane.clear();
            for (int i=0;i<4;i++) lanePointers[i]=0;
            for (Note n : guitar) { n.hit=false; n.done=false; }
            for (Note n : drums) { n.hit=false; n.done=false; }
            if (music != null) {
                try { if (music.isPlaying()) music.pause(); music.seekTo(0); } catch (Exception ignored) {}
            }
            songEpoch = SystemClock.elapsedRealtime() + PREROLL_MS;
            invalidate();
        }

        void backToChooser() {
            if (music != null) try { if (music.isPlaying()) music.pause(); music.seekTo(0); } catch (Exception ignored) {}
            choosing=true; finished=false; audioStarted=false; feedback="";
            invalidate();
        }

        long songTime(long now) {
            if (audioStarted && music != null) {
                try { return music.getCurrentPosition(); } catch (Exception ignored) {}
            }
            return now - songEpoch;
        }

        @Override protected void onDraw(Canvas c) {
            long now = SystemClock.elapsedRealtime();
            if (choosing) { drawChooser(c); return; }
            if (!audioStarted && now >= songEpoch) {
                audioStarted=true;
                if (music != null) try { music.start(); } catch (Exception ignored) {}
            }
            long song = songTime(now);
            update(song, now);
            drawGame(c, song, now);
            postInvalidateOnAnimation();
        }

        void update(long song, long now) {
            if (finished || song < -TRAVEL_MS) return;
            for (Note n : chart()) {
                if (n.done) continue;
                if (!n.hit && song > n.timeMs + GOOD_MS) {
                    n.done=true;
                    applyResult(3, now);
                } else if (n.hit && n.durationMs > 0 && song >= n.timeMs + n.durationMs - 70) {
                    if (lanePointers[n.lane] > 0) {
                        n.done=true;
                        score += 250;
                        feedback="HOLD!";
                        feedbackUntil=now+250;
                    } else {
                        n.done=true;
                        applyResult(3, now);
                    }
                }
            }
            if (song > SONG_MS + 700) { finished=true; feedback="SONG COMPLETE"; }
        }

        void attemptHit(int lane, long song, long now) {
            if (finished) { backToChooser(); return; }
            Note best=null; long bestDiff=Long.MAX_VALUE;
            for (Note n : chart()) {
                if (n.done || n.hit || n.lane != lane) continue;
                long diff=Math.abs(song-n.timeMs);
                if (diff < bestDiff) { best=n; bestDiff=diff; }
                if (n.timeMs > song + GOOD_MS) break;
            }
            if (best==null || bestDiff>GOOD_MS) {
                feedback="EARLY / LATE"; feedbackUntil=now+250; return;
            }
            best.hit=true;
            lastPlayedLane=lane;
            frogPlayUntil=now+170;
            int result = bestDiff<=PERFECT_MS ? 0 : bestDiff<=GREAT_MS ? 1 : 2;
            applyResult(result, now);
            if (best.durationMs==0) best.done=true;
        }

        void releaseLane(int lane, long song, long now) {
            for (Note n : chart()) {
                if (!n.done && n.hit && n.lane==lane && n.durationMs>0) {
                    if (song < n.timeMs+n.durationMs-100) {
                        n.done=true;
                        applyResult(3, now);
                        feedback="HOLD RELEASED";
                        feedbackUntil=now+500;
                    }
                }
            }
        }

        void applyResult(int result, long now) {
            if (result==0) {
                missStreak=0; perfectStreak++; combo++;
                score += 1000 + Math.min(combo,50)*10;
                frogState = perfectStreak>=5 ? 2 : 0;
                feedback="PERFECT";
            } else if (result==1) {
                missStreak=0; perfectStreak=0; combo++;
                score += 650 + Math.min(combo,50)*5;
                frogState=0; feedback="GREAT";
            } else if (result==2) {
                missStreak=0; perfectStreak=0; combo++;
                score += 350; frogState=0; feedback="GOOD";
            } else {
                perfectStreak=0; missStreak++; combo=0;
                frogState = missStreak>=3 ? 1 : 0;
                feedback="MISS";
            }
            bestCombo=Math.max(bestCombo,combo);
            if (frogState==1) feedback += "  BLUE SHOCK!";
            else if (frogState==2) feedback += "  ON FIRE!";
            feedbackUntil=now+520;
        }

        @Override public boolean onTouchEvent(MotionEvent e) {
            int action=e.getActionMasked();
            int index=e.getActionIndex();
            long now=SystemClock.elapsedRealtime();
            if (choosing) {
                if (action==MotionEvent.ACTION_DOWN) {
                    float y=e.getY();
                    if (y > getHeight()*0.30f && y < getHeight()*0.58f) startSong(GUITAR);
                    else if (y >= getHeight()*0.62f && y < getHeight()*0.90f) startSong(DRUMS);
                }
                return true;
            }
            if (action==MotionEvent.ACTION_DOWN || action==MotionEvent.ACTION_POINTER_DOWN) {
                if (e.getY(index) < getHeight()*0.10f && e.getX(index) < getWidth()*0.22f) { backToChooser(); return true; }
                int pointer=e.getPointerId(index);
                int lane=Math.max(0,Math.min(3,(int)(e.getX(index)/(getWidth()/4f))));
                pointerLane.put(pointer,lane); lanePointers[lane]++;
                attemptHit(lane,songTime(now),now);
            } else if (action==MotionEvent.ACTION_UP || action==MotionEvent.ACTION_POINTER_UP) {
                int pointer=e.getPointerId(index);
                int lane=pointerLane.get(pointer,-1);
                if (lane>=0) {
                    pointerLane.delete(pointer);
                    lanePointers[lane]=Math.max(0,lanePointers[lane]-1);
                    if (lanePointers[lane]==0) releaseLane(lane,songTime(now),now);
                }
            } else if (action==MotionEvent.ACTION_CANCEL) {
                for (int lane=0;lane<4;lane++) {
                    if (lanePointers[lane]>0) releaseLane(lane,songTime(now),now);
                    lanePointers[lane]=0;
                }
                pointerLane.clear();
            }
            return true;
        }

        void drawChooser(Canvas c) {
            c.drawColor(Color.rgb(7,18,12));
            text(c,"FROG BAND",getWidth()/2f,getHeight()*0.10f,getHeight()*0.050f,Color.WHITE,true);
            text(c,"FRANTIC FROG",getWidth()/2f,getHeight()*0.16f,getHeight()*0.025f,Color.rgb(147,230,151),true);
            text(c,"CHOOSE YOUR FROG",getWidth()/2f,getHeight()*0.22f,getHeight()*0.022f,Color.LTGRAY,true);
            drawChoiceCard(c,GUITAR,getHeight()*0.30f,getHeight()*0.58f,"GUITAR FROG","4-LANE GUITAR");
            drawChoiceCard(c,DRUMS,getHeight()*0.62f,getHeight()*0.90f,"DRUM FROG","4-LANE DRUMS");
        }

        void drawChoiceCard(Canvas c,int which,float top,float bottom,String title,String subtitle) {
            float l=getWidth()*0.08f,r=getWidth()*0.92f;
            p.setColor(Color.rgb(20,48,31)); c.drawRoundRect(l,top,r,bottom,d(22),d(22),p);
            p.setColor(which==GUITAR?Color.rgb(215,68,62):Color.rgb(235,176,48));
            c.drawRoundRect(l,top,l+d(10),bottom,d(10),d(10),p);
            float x=l+(r-l)*0.25f,y=(top+bottom)/2f;
            drawFrog(c,x,y,which,SystemClock.elapsedRealtime(),true);
            textLeft(c,title,l+(r-l)*0.47f,y-d(9),d(22),Color.WHITE);
            textLeft(c,subtitle,l+(r-l)*0.47f,y+d(18),d(13),Color.rgb(190,213,194));
            text(c,"PLAY",r-d(42),y+d(5),d(12),Color.rgb(143,229,149),true);
        }

        void drawGame(Canvas c,long song,long now) {
            c.drawColor(Color.rgb(7,17,11));
            float w=getWidth(),h=getHeight();
            float hitY=h*0.65f;
            float spawnY=h*0.34f;
            float laneW=w/4f;

            p.setColor(Color.rgb(18,43,28)); c.drawRect(0,0,w,h*0.31f,p);
            text(c,"BACK",w*0.09f,h*0.05f,d(12),Color.LTGRAY,true);
            text(c,instrument==GUITAR?"GUITAR FROG":"DRUM FROG",w/2f,h*0.045f,d(16),Color.WHITE,true);
            text(c,"SCORE "+score+"    COMBO x"+combo,w/2f,h*0.085f,d(12),Color.rgb(215,230,217),true);
            drawFrog(c,w/2f,h*0.205f,instrument,now,false);

            for (int i=0;i<4;i++) {
                float l=i*laneW;
                p.setColor(i%2==0?Color.rgb(12,28,19):Color.rgb(15,33,22));
                c.drawRect(l,h*0.31f,l+laneW,h,p);
                stroke.setColor(Color.argb(100,255,255,255)); stroke.setStrokeWidth(d(1));
                c.drawLine(l,h*0.31f,l,h,stroke);
            }
            c.drawLine(w-1,h*0.31f,w-1,h,stroke);

            for (Note n : chart()) {
                if (n.done && !n.hit) continue;
                long delta=n.timeMs-song;
                if (delta>TRAVEL_MS+200 || delta<-GOOD_MS-500) continue;
                float headY=hitY-(delta/(float)TRAVEL_MS)*(hitY-spawnY);
                float cx=(n.lane+.5f)*laneW;
                if (n.durationMs>0) {
                    long endDelta=(n.timeMs+n.durationMs)-song;
                    float tailY=hitY-(endDelta/(float)TRAVEL_MS)*(hitY-spawnY);
                    float top=Math.min(headY,tailY),bot=Math.max(headY,tailY);
                    p.setColor(Color.argb(n.hit?180:120, Color.red(laneColors[n.lane]),Color.green(laneColors[n.lane]),Color.blue(laneColors[n.lane])));
                    c.drawRoundRect(cx-laneW*0.13f,top,cx+laneW*0.13f,bot,d(10),d(10),p);
                }
                p.setColor(n.hit?Color.WHITE:laneColors[n.lane]);
                c.drawRoundRect(cx-laneW*0.28f,headY-d(12),cx+laneW*0.28f,headY+d(12),d(10),d(10),p);
            }

            p.setColor(Color.WHITE); c.drawRect(0,hitY-d(3),w,hitY+d(3),p);
            text(c,"HIT",w/2f,hitY-d(10),d(10),Color.WHITE,true);

            String[] labels=instrument==GUITAR?guitarLabels:drumLabels;
            for (int i=0;i<4;i++) {
                float l=i*laneW,r=l+laneW;
                p.setColor(lanePointers[i]>0?laneColors[i]:Color.argb(120,Color.red(laneColors[i]),Color.green(laneColors[i]),Color.blue(laneColors[i])));
                c.drawRoundRect(l+d(5),hitY+d(14),r-d(5),h-d(12),d(16),d(16),p);
                text(c,labels[i],(l+r)/2f,hitY+(h-hitY)*0.48f,d(11),Color.WHITE,true);
                text(c,"TAP / HOLD",(l+r)/2f,hitY+(h-hitY)*0.65f,d(8),Color.WHITE,true);
            }

            if (song<0) {
                int count=(int)Math.ceil((-song)/700.0);
                text(c,count>0?String.valueOf(count):"GO!",w/2f,h*0.47f,d(44),Color.WHITE,true);
            } else if (now<feedbackUntil) {
                int col=frogState==1?Color.CYAN:frogState==2?Color.rgb(255,130,30):Color.WHITE;
                text(c,feedback,w/2f,h*0.30f,d(14),col,true);
            }
            if (finished) {
                p.setColor(Color.argb(220,5,13,9)); c.drawRect(0,h*0.34f,w,h*0.62f,p);
                text(c,"SONG COMPLETE",w/2f,h*0.44f,d(30),Color.WHITE,true);
                text(c,"SCORE "+score+"   BEST COMBO "+bestCombo,w/2f,h*0.50f,d(15),Color.rgb(151,231,157),true);
                text(c,"Tap any lane to choose again",w/2f,h*0.56f,d(12),Color.LTGRAY,true);
            }
        }

        void drawFrog(Canvas c,float x,float y,int which,long now,boolean small) {
            float s=small?0.75f:1.25f;
            boolean playing=now<frogPlayUntil;
            if (playing) y-=d(5)*s;
            if (frogState==2 && !small) drawFire(c,x,y,s);
            if (frogState==1 && !small) drawShock(c,x,y,s);
            int green=(frogState==1&&!small)?Color.rgb(67,146,218):Color.rgb(89,181,77);
            p.setColor(green);
            c.drawOval(x-d(34)*s,y-d(24)*s,x+d(34)*s,y+d(38)*s,p);
            c.drawCircle(x-d(21)*s,y-d(30)*s,d(14)*s,p); c.drawCircle(x+d(21)*s,y-d(30)*s,d(14)*s,p);
            p.setColor(Color.WHITE); c.drawCircle(x-d(21)*s,y-d(31)*s,d(7)*s,p); c.drawCircle(x+d(21)*s,y-d(31)*s,d(7)*s,p);
            p.setColor(Color.BLACK); c.drawCircle(x-d(21)*s,y-d(31)*s,d(3)*s,p); c.drawCircle(x+d(21)*s,y-d(31)*s,d(3)*s,p);
            if (which==GUITAR) drawGuitar(c,x,y,s,playing); else drawDrums(c,x,y,s,playing);
        }

        void drawGuitar(Canvas c,float x,float y,float s,boolean playing) {
            p.setColor(Color.rgb(205,63,57)); c.drawOval(x-d(7)*s,y+d(8)*s,x+d(39)*s,y+d(35)*s,p);
            stroke.setStrokeWidth(d(6)*s); stroke.setColor(Color.rgb(229,204,151));
            c.drawLine(x+d(18)*s,y+d(16)*s,x-d(46)*s,y-d(18)*s,stroke);
            stroke.setStrokeWidth(d(3)*s); stroke.setColor(Color.WHITE);
            float m=playing?(lastPlayedLane-1.5f)*d(5)*s:0;
            c.drawLine(x-d(8)*s,y+m,x+d(29)*s,y+d(30)*s-m,stroke);
        }

        void drawDrums(Canvas c,float x,float y,float s,boolean playing) {
            p.setColor(Color.rgb(225,168,45));
            c.drawOval(x-d(34)*s,y+d(17)*s,x+d(7)*s,y+d(41)*s,p);
            c.drawOval(x+d(4)*s,y+d(13)*s,x+d(39)*s,y+d(37)*s,p);
            stroke.setColor(Color.rgb(220,202,150)); stroke.setStrokeWidth(d(3)*s);
            float swing=playing?d(12)*s:0;
            c.drawLine(x-d(18)*s,y-d(1)*s,x-d(31)*s,y+d(22)*s-swing,stroke);
            c.drawLine(x+d(18)*s,y-d(1)*s,x+d(31)*s,y+d(20)*s-swing,stroke);
        }

        void drawFire(Canvas c,float x,float y,float s) {
            Path path=new Path();
            for (int i=-3;i<=3;i++) {
                float fx=x+i*d(16)*s; path.reset();
                path.moveTo(fx-d(8)*s,y+d(45)*s); path.lineTo(fx,y-d((i&1)==0?65:50)*s); path.lineTo(fx+d(8)*s,y+d(45)*s); path.close();
                p.setColor(Color.rgb(255,107,30)); c.drawPath(path,p);
            }
        }

        void drawShock(Canvas c,float x,float y,float s) {
            stroke.setColor(Color.CYAN); stroke.setStrokeWidth(d(4)*s);
            for (int i=-2;i<=2;i++) {
                Path z=new Path(); float sx=x+i*d(22)*s;
                z.moveTo(sx,y-d(58)*s); z.lineTo(sx-d(7)*s,y-d(37)*s); z.lineTo(sx+d(8)*s,y-d(27)*s); z.lineTo(sx-d(4)*s,y-d(6)*s);
                c.drawPath(z,stroke);
            }
        }

        float d(float dp) { return dp*getResources().getDisplayMetrics().density; }
        void text(Canvas c,String s,float x,float y,float size,int color,boolean center) {
            p.setTypeface(Typeface.create(Typeface.DEFAULT,Typeface.BOLD)); p.setTextSize(size); p.setColor(color); p.setTextAlign(center?Paint.Align.CENTER:Paint.Align.LEFT); c.drawText(s,x,y,p);
        }
        void textLeft(Canvas c,String s,float x,float y,float size,int color) { text(c,s,x,y,size,color,false); }

        @Override protected void onDetachedFromWindow() {
            super.onDetachedFromWindow();
            if (music!=null) { try { music.release(); } catch(Exception ignored){} music=null; }
        }
    }
}
