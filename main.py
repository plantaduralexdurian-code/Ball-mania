from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from random import random, uniform, choice
import math

BARRA_ALTURA = 90
EVENTO_DURACION = 20
MINI_SCALE = 2 / 3

# --- CLASES DE BOLAS ---
class Bola:
    def __init__(self, parent, x, y, rainbow=False, giant=False, mini=False):
        self.parent = parent
        self.base_size = uniform(25, 60)
        self.factor_actual = 2.0 if giant else (MINI_SCALE if mini else 1.0)
        self.size = self.base_size * self.factor_actual
        self.vx = uniform(-220, 220)
        self.vy = uniform(-220, 220)
        self.rainbow = rainbow
        self.hue = random()
        self.base_color = (uniform(0.3, 1), uniform(0.3, 1), uniform(0.3, 1))

        with parent.canvas.before:
            self.color_instr = Color(*self.base_color, 1)
            self.circle = Ellipse(size=(self.size, self.size))
            self.border_color_instr = Color(0, 0, 0, 1)
            self.border = Line(width=1)

        r = self.size / 2
        self.circle.pos = (x - r, y - r)
        self.actualizar_borde()

    def actualizar_borde(self):
        x, y = self.circle.pos
        r = self.size / 2
        self.border.circle = (x + r, y + r, r)

    def set_scale(self, nuevo_factor):
        centro_x = self.circle.pos[0] + self.size / 2
        centro_y = self.circle.pos[1] + self.size / 2
        self.factor_actual = nuevo_factor
        self.size = self.base_size * self.factor_actual
        self.circle.size = (self.size, self.size)
        r = self.size / 2
        self.circle.pos = (centro_x - r, centro_y - r)
        self.actualizar_borde()

    def update_color(self, dt):
        if self.rainbow:
            self.hue = (self.hue + dt * 0.15) % 1
            self.color_instr.hsv = (self.hue, 0.6, 1)
        else:
            self.color_instr.rgb = self.base_color

    def move(self, dt, speed):
        x, y = self.circle.pos
        x += self.vx * dt * speed
        y += self.vy * dt * speed
        if x <= 0: x = 0; self.vx = abs(self.vx)
        elif x + self.size >= self.parent.width: x = self.parent.width - self.size; self.vx = -abs(self.vx)
        if y <= BARRA_ALTURA: y = BARRA_ALTURA; self.vy = abs(self.vy)
        elif y + self.size >= self.parent.height: y = self.parent.height - self.size; self.vy = -abs(self.vy)
        self.circle.pos = (x, y); self.actualizar_borde()

    def limpiar(self):
        try:
            self.parent.canvas.before.remove(self.circle)
            self.parent.canvas.before.remove(self.border)
            self.parent.canvas.before.remove(self.color_instr)
            self.parent.canvas.before.remove(self.border_color_instr)
        except: pass

class BolaColisionable(Bola):
    def move(self, dt, speed):
        super().move(dt, speed)
        for otra in self.parent.bolas:
            if otra is self or not isinstance(otra, BolaColisionable): continue
            dx = (self.circle.pos[0] + self.size/2) - (otra.circle.pos[0] + otra.size/2)
            dy = (self.circle.pos[1] + self.size/2) - (otra.circle.pos[1] + otra.size/2)
            distancia = math.sqrt(dx*dx + dy*dy)
            min_dist = (self.size/2) + (otra.size/2)
            if distancia < min_dist:
                self.vx, otra.vx = otra.vx, self.vx
                self.vy, otra.vy = otra.vy, self.vy

class BolaFragmento(Bola):
    def __init__(self, parent, x, y):
        super().__init__(parent, x, y, rainbow=True, mini=True)
        self.vida = 10.0
    def move(self, dt, speed):
        super().move(dt, speed); self.vida -= dt
        if self.vida <= 0: self.parent.eliminar_bola(self)

class BolaEvolutiva(Bola):
    def __init__(self, parent, x, y):
        super().__init__(parent, x, y, rainbow=True)
        self.vida = 10.0
        self.en_colision = False
        self.limite_tamano = 400 
    def move(self, dt, speed):
        x, y = self.circle.pos
        toca_pared = False
        x += self.vx * dt * speed
        y += self.vy * dt * speed
        if x <= 0: x = 0; self.vx = abs(self.vx); toca_pared = True
        elif x + self.size >= self.parent.width: x = self.parent.width - self.size; self.vx = -abs(self.vx); toca_pared = True
        if y <= BARRA_ALTURA: y = BARRA_ALTURA; self.vy = abs(self.vy); toca_pared = True
        elif y + self.size >= self.parent.height: y = self.parent.height - self.size; self.vy = -abs(self.vy); toca_pared = True
        if toca_pared:
            if not self.en_colision:
                if self.size < self.limite_tamano: self.set_scale(self.factor_actual * 1.30)
                self.en_colision = True
        else: self.en_colision = False
        self.circle.pos = (x, y); self.actualizar_borde()
        self.vida -= dt
        if self.vida <= 0: self.explotar()
    def explotar(self):
        cx, cy = self.circle.pos[0] + self.size/2, self.circle.pos[1] + self.size/2
        self.parent.eliminar_bola(self)
        for i in range(8):
            ang = (2 * math.pi / 8) * i
            nx, ny = cx + math.cos(ang) * 10, max(cy + math.sin(ang) * 10, BARRA_ALTURA + 15)
            f = BolaFragmento(self.parent, nx, ny)
            f.vx, f.vy = math.cos(ang) * 480, math.sin(ang) * 480
            self.parent.bolas.append(f)
            self.parent.total_bolas += 1 
        self.parent.actualizar_label_contador()

# --- JUEGO PRINCIPAL ---
class Juego(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bolas, self.paused, self.speed_scale = [], False, 1
        self.evento_timer, self.total_bolas, self.total_rainbow = 0, 0, 0
        self.total_crecientes, self.total_eventos, self.tiempo, self.bg_hue = 0, 0, 0, 0
        
        with self.canvas.before:
            self.bg_color = Color(1, 1, 1, 1)
            self.bg = Rectangle(pos=self.pos, size=self.size)
            self.barra_color = Color(0.95, 0.95, 0.95, 1)
            self.barra_rect = Rectangle(pos=(0, 0), size=(self.width, BARRA_ALTURA))
        
        self.bind(size=self._resize, pos=self._resize)
        self._crear_ui_paneles()
        self._crear_ui_botones()
        
        self.lbl_evento = Label(text="", color=(0,0,0,1), font_size=26, bold=True, size_hint=(None, None), size=(400, 50), pos_hint={"center_x": 0.5, "top": 0.98})
        self.add_widget(self.lbl_evento)
        
        Clock.schedule_interval(self.update, 1 / 60)

    def _resize(self, *args):
        self.bg.size, self.barra_rect.size = self.size, (self.width, BARRA_ALTURA)
        ancho_p, alto_p = self.width * 0.8, self.height * 0.7
        pos_x, pos_y = self.width * 0.1, self.height * 0.15
        
        for panel, bg in [(self.stats_panel, self.stats_bg), (self.debug_panel, self.debug_bg)]:
            panel.size = (ancho_p, alto_p)
            panel.pos = (pos_x, pos_y)
            bg.size = (ancho_p, alto_p)
            bg.pos = (pos_x, pos_y)

    def _crear_ui_botones(self):
        self.ui_inferior = FloatLayout(size_hint=(1, None), height=BARRA_ALTURA)
        self.btn_evento = Button(text="Evento", size_hint=(.25, 1), pos_hint={"x": 0})
        self.btn_evento.bind(on_release=self.evento)
        self.btn_pausa = Button(text="Pausa", size_hint=(.25, 1), pos_hint={"x": .25})
        self.btn_pausa.bind(on_release=self.toggle_pausa)
        self.btn_reset = Button(text="reset", size_hint=(.25, 1), pos_hint={"x": .5})
        self.btn_reset.bind(on_release=self.reset)
        self.lbl_contador = Label(text="Bolas: 0", color=(0,0,0,1), size_hint=(.25, 1), pos_hint={"x": .75})
        
        self.ui_inferior.add_widget(self.btn_evento); self.ui_inferior.add_widget(self.btn_pausa)
        self.ui_inferior.add_widget(self.btn_reset); self.ui_inferior.add_widget(self.lbl_contador)
        self.add_widget(self.ui_inferior)
        
        self.btn_stats = Button(text="?", size_hint=(None, None), size=(70, 70), pos_hint={"x": 0.01, "top": 0.99})
        self.btn_stats.bind(on_release=self.mostrar_stats); self.add_widget(self.btn_stats)
        
        self.btn_debug_trigger = Button(text="!", size_hint=(None, None), size=(70, 70), pos_hint={"right": 0.99, "top": 0.99}, background_color=(1,0,0,1))
        self.btn_debug_trigger.bind(on_release=self.mostrar_debug); self.add_widget(self.btn_debug_trigger)

    def _crear_ui_paneles(self):
        # Stats
        self.stats_panel = FloatLayout(opacity=0, disabled=True, size_hint=(None, None))
        with self.stats_panel.canvas.before:
            Color(1, 1, 1, .95); self.stats_bg = RoundedRectangle(radius=[25])
        self.stats_label = Label(text="", color=(0,0,0,1), halign="left", valign="top", size_hint=(.9, .6), pos_hint={"center_x": .5, "center_y": .6})
        self.stats_label.bind(size=self.stats_label.setter("text_size"))
        btn_c = Button(text="Cerrar", size_hint=(None, None), size=(140, 45), pos_hint={"center_x": .5, "y": .1})
        btn_c.bind(on_release=self.ocultar_paneles); self.stats_panel.add_widget(self.stats_label); self.stats_panel.add_widget(btn_c); self.add_widget(self.stats_panel)
        
        # Debug
        self.debug_panel = FloatLayout(opacity=0, disabled=True, size_hint=(None, None))
        with self.debug_panel.canvas.before:
            Color(.1, .1, .1, .95); self.debug_bg = RoundedRectangle(radius=[25])
        
        # Grid para los botones de debug con más espacio
        grid = GridLayout(cols=2, spacing=15, size_hint=(.9, .7), pos_hint={"center_x": .5, "center_y": .55})
        
        # Opciones actualizadas con nombres completos y fuente más grande
        opc = [
            ("Rainbow", lambda x: self.crear_bola_especifica("RAINBOW")), 
            ("Creciente", lambda x: self.crear_bola_especifica("CRECIENTE")), 
            ("Colisión", lambda x: self.crear_bola_especifica("COLISION")), 
            ("Gigante", lambda x: self.crear_bola_especifica("GIGANTE")),
            ("Evento RAINBOW", lambda x: self.forzar_evento("RAINBOW")), 
            ("Evento MINI", lambda x: self.forzar_evento("MINI")), 
            ("Evento GIANT", lambda x: self.forzar_evento("GIANT")), 
            ("Evento SPEED", lambda x: self.forzar_evento("SPEED")),
            ("Evento SLOWED", lambda x: self.forzar_evento("SLOWED")), 
            ("Ocultar UI", self.toggle_ui_visibility)
        ]
        
        for t, f in opc:
            # Font size aumentado a 18 (era 14)
            b = Button(text=t, font_size=18, bold=True)
            b.bind(on_release=f)
            grid.add_widget(b)
            
        btn_d = Button(text="Cerrar Debug", size_hint=(None, None), size=(180, 55), pos_hint={"center_x": .5, "y": .05}, font_size=18)
        btn_d.bind(on_release=self.ocultar_paneles)
        self.debug_panel.add_widget(grid)
        self.debug_panel.add_widget(btn_d)
        self.add_widget(self.debug_panel)

    def on_touch_down(self, touch):
        for panel, bg in [(self.stats_panel, self.stats_bg), (self.debug_panel, self.debug_bg)]:
            if panel.opacity > 0:
                x, y = bg.pos
                w, h = bg.size
                if not (x <= touch.x <= x + w and y <= touch.y <= y + h):
                    self.ocultar_paneles()
                    return True
                return super(Juego, self).on_touch_down(touch)
        if self.ui_inferior.collide_point(*touch.pos):
            return super(Juego, self).on_touch_down(touch)
        if self.btn_stats.collide_point(*touch.pos) or self.btn_debug_trigger.collide_point(*touch.pos):
            return super(Juego, self).on_touch_down(touch)
        if not self.paused and touch.y > BARRA_ALTURA:
            self.crear_bola(touch.x, touch.y)
            return True
        return False

    def on_touch_move(self, touch):
        if not self.paused and touch.y > BARRA_ALTURA and self.stats_panel.opacity == 0 and self.debug_panel.opacity == 0:
            self.crear_bola(touch.x, touch.y)
            return True
        return False

    def mostrar_stats(self, *_):
        self.paused = True
        m, s = divmod(int(self.tiempo), 60)
        self.stats_label.text = f"ESTADÍSTICAS\n\nBolas totales: {self.total_bolas}\nBolas rainbow: {self.total_rainbow}\nBolas crecientes: {self.total_crecientes}\nTiempo: {m:02d}:{s:02d}"
        self.stats_panel.opacity, self.stats_panel.disabled = 1, False

    def mostrar_debug(self, *_):
        self.paused, self.debug_panel.opacity, self.debug_panel.disabled = True, 1, False

    def ocultar_paneles(self, *_):
        self.stats_panel.opacity, self.stats_panel.disabled = 0, True
        self.debug_panel.opacity, self.debug_panel.disabled = 0, True
        self.paused = False

    def crear_bola(self, x, y):
        if random() < 0.15: bola = BolaEvolutiva(self, x, y); self.total_crecientes += 1
        else:
            rb = random() < 0.25 or "RAINBOW" in self.lbl_evento.text
            bola = Bola(self, x, y, rb, "GIANT" in self.lbl_evento.text, "MINI" in self.lbl_evento.text)
            if rb: self.total_rainbow += 1
        self.bolas.append(bola); self.total_bolas += 1; self.actualizar_label_contador()

    def toggle_ui_visibility(self, *_): self.ui_inferior.opacity = self.btn_stats.opacity = 0 if self.ui_inferior.opacity == 1 else 1
    
    def crear_bola_especifica(self, t):
        x, y = self.width/2, self.height/2
        if t=="RAINBOW": b=Bola(self, x, y, rainbow=True); self.total_rainbow+=1
        elif t=="CRECIENTE": b=BolaEvolutiva(self, x, y); self.total_crecientes+=1
        elif t=="COLISION": b=BolaColisionable(self, x, y)
        elif t=="GIGANTE": b=Bola(self, x, y, giant=True)
        self.bolas.append(b); self.total_bolas+=1; self.actualizar_label_contador()
    
    def forzar_evento(self, t):
        self.evento_timer, self.lbl_evento.text = EVENTO_DURACION, f"Evento: {t}"
        self.speed_scale = 4 if t=="SPEED" else (0.35 if t=="SLOWED" else 1)
        for b in self.bolas:
            if t=="RAINBOW": b.rainbow=True
            elif t=="GIANT": b.set_scale(2.0)
            elif t=="MINI": b.set_scale(MINI_SCALE)
            else: b.set_scale(1.0)

    def evento(self, *_): self.forzar_evento(choice(["SPEED", "SLOWED", "RAINBOW", "GIANT", "MINI"]))
    def toggle_pausa(self, *_): self.paused = not self.paused; self.btn_pausa.text = "Reanudar" if self.paused else "Pausa"
    def reset(self, *_):
        for b in self.bolas: b.limpiar()
        self.bolas.clear(); self.actualizar_label_contador(); self.lbl_evento.text, self.evento_timer, self.speed_scale = "", 0, 1
    def eliminar_bola(self, b): 
        if b in self.bolas: self.bolas.remove(b); b.limpiar(); self.actualizar_label_contador()
    def actualizar_label_contador(self): self.lbl_contador.text = f"Bolas: {len(self.bolas)}"
    def update(self, dt):
        self.bg_hue = (self.bg_hue + dt * 0.02) % 1
        self.bg_color.hsv = (self.bg_hue, 0.1, 1)
        if self.paused: return
        self.tiempo += dt
        if self.evento_timer > 0:
            self.evento_timer -= dt
            if self.evento_timer <= 0:
                self.speed_scale = 1
                for b in self.bolas:
                    if not isinstance(b, (BolaEvolutiva, BolaFragmento)): b.rainbow = False
                    b.set_scale(1.0)
                self.lbl_evento.text = ""
        for b in self.bolas[:]: b.move(dt, self.speed_scale); b.update_color(dt)

class JuegoApp(App):
    def build(self): return Juego()

if __name__ == "__main__":
    JuegoApp().run()
