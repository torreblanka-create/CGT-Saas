import io
import math

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def draw_rigging_diagram(d1, d2, l1=0, l2=0, angulo=60, asimetrico=True, tandem=False):
    """
    Genera un diagrama de rigging asimétrico o simétrico estilo Blueprint Industrial.
    Soporta modo Tándem (2 grúas).
    """
    fig, ax = plt.subplots(figsize=(7, 5), facecolor='#0B132B')
    ax.set_facecolor('#0B132B')

    base_length = (d1 + d2) if asimetrico else 2.0
    d1_v = d1 if asimetrico else 1.0
    d2_v = d2 if asimetrico else 1.0

    # Dibujar Carga con achurado
    rect = patches.Rectangle((0, -0.6), base_length, 0.6, facecolor='#1C2541', edgecolor='#47A8BD', linewidth=2, hatch='///', zorder=2)
    ax.add_patch(rect)

    if tandem:
        # En Tándem tenemos 2 ganchos, uno en cada extremo (o cerca)
        hook_a_x = base_length * 0.1
        hook_b_x = base_length * 0.9
        h = base_length * 0.5 # Altura simplificada para tandem
        
        # Grúa A (Izquierda)
        ax.plot([hook_a_x, hook_a_x], [0, h], color='#F26419', linewidth=3, zorder=1)
        ax.scatter(hook_a_x, h, s=200, color='#F26419', marker='^', zorder=5, edgecolor='white')
        ax.plot([hook_a_x, hook_a_x], [h, h + 1], color='#FFFFFF', linestyle='-.', linewidth=2, zorder=1)
        ax.annotate("GRÚA A", xy=(hook_a_x, h + 1.2), ha='center', color='#F26419', fontsize=9, fontweight='bold')
        
        # Grúa B (Derecha)
        ax.plot([hook_b_x, hook_b_x], [0, h], color='#F6AE2D', linewidth=3, zorder=1)
        ax.scatter(hook_b_x, h, s=200, color='#F6AE2D', marker='^', zorder=5, edgecolor='white')
        ax.plot([hook_b_x, hook_b_x], [h, h + 1], color='#FFFFFF', linestyle='-.', linewidth=2, zorder=1)
        ax.annotate("GRÚA B", xy=(hook_b_x, h + 1.2), ha='center', color='#F6AE2D', fontsize=9, fontweight='bold')
        
        ax.set_title(f"BLUEPRINT: Maniobra TÁNDEM (2 Grúas)", fontsize=12, fontweight='bold', color='#47A8BD', fontfamily='monospace', loc='left', pad=20)
    else:
        # Modo estándar (1 grúa)
        hook_x = d1_v
        ang_rad = math.radians(angulo)
        h = max(d1_v, d2_v) * math.tan(ang_rad) if base_length > 0 else 2.0

        # Eslingas
        ax.plot([0, hook_x], [0, h], color='#F26419', linewidth=3, zorder=1)
        ax.plot([base_length, hook_x], [0, h], color='#F6AE2D', linewidth=3, zorder=1)

        # Gancho
        ax.scatter(hook_x, h, s=300, color='#F6AE2D', marker='^', zorder=5, edgecolor='white', linewidth=1.5)
        ax.plot([hook_x, hook_x], [h, h + 1], color='#FFFFFF', linestyle='-.', linewidth=2, zorder=1)
        
        # Texto Angulo
        ax.annotate(f"Ángulo: {angulo}°", xy=(hook_x, h - 0.5), ha='center', color='#F6AE2D', fontsize=11, fontweight='bold', bbox=dict(boxstyle='round,pad=0.2', facecolor='#0B132B', edgecolor='none'))
        ax.set_title(f"BLUEPRINT: Esquema de Izaje {'Asimétrico' if asimetrico else 'Simétrico'}", fontsize=12, fontweight='bold', color='#47A8BD', fontfamily='monospace', loc='left', pad=20)

    # Centro de Gravedad
    ax.scatter(d1_v, -0.3, s=150, color='#E71D36', marker='+', zorder=6, linewidths=3)
    circle_cg = patches.Circle((d1_v, -0.3), 0.1, fill=False, color='#E71D36', linewidth=2, zorder=6)
    ax.add_patch(circle_cg)
    ax.annotate("CG", xy=(d1_v, -0.05), ha='center', color='#FFFFFF', fontsize=10, fontweight='bold')

    # Cotas (Dimensiones D1, D2)
    if asimetrico:
        ax.annotate('', xy=(0, -0.9), xytext=(d1_v, -0.9), arrowprops=dict(arrowstyle='<->', color='#3A506B', lw=1.5))
        ax.annotate(f"D1 = {d1}m", xy=(d1_v/2, -1.1), ha='center', color='#47A8BD', fontsize=10, fontweight='bold')
        
        ax.annotate('', xy=(d1_v, -0.9), xytext=(base_length, -0.9), arrowprops=dict(arrowstyle='<->', color='#3A506B', lw=1.5))
        ax.annotate(f"D2 = {d2}m", xy=(d1_v + d2_v/2, -1.1), ha='center', color='#47A8BD', fontsize=10, fontweight='bold')

    # Línea horizontal base
    ax.plot([0, base_length], [0, 0], color='#FFFFFF', linestyle=':', linewidth=1)
    
    ax.set_aspect('equal', adjustable='datalim')
    ax.axis('off')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none', dpi=200)
    buf.seek(0)
    plt.close()
    return buf.getvalue()

def draw_lmi_chart(radios, capacidades, current_radio, current_bruta_kg):
    """
    Genera gráfico LMI estilo On-Board Screen.
    """
    if not radios or not capacidades: return None

    cap_t = [c / 1000.0 for c in capacidades]
    bruta_t = current_bruta_kg / 1000.0

    fig, ax = plt.subplots(figsize=(6, 4), facecolor='#050505')
    ax.set_facecolor('#0A0A0A')

    # Encontrar la capacidad teórica en el radio actual interpolando
    try: cap_max_at_radio = np.interp(current_radio, radios, cap_t)
    except: cap_max_at_radio = max(cap_t)

    # Plot Curva Limite
    ax.plot(radios, cap_t, color='#00E5FF', linewidth=3, zorder=3, label='Curva de Diseño LMI')
    
    # Zonas
    ax.fill_between(radios, cap_t, color='#00E5FF', alpha=0.15, zorder=1)
    ax.fill_between(radios, cap_t, max(cap_t)*1.5, color='#FF1744', alpha=0.1, zorder=1)

    # Color del punto según estrés
    util_ratio = (bruta_t / cap_max_at_radio) if cap_max_at_radio > 0 else 2.0
    if util_ratio < 0.75: color_punto = '#00E676' # Verde
    elif util_ratio <= 1.0: color_punto = '#FFEA00' # Amarillo
    else: color_punto = '#FF1744' # Rojo

    # Punto
    ax.scatter(current_radio, bruta_t, color=color_punto, s=120, zorder=5, edgecolor='white', linewidth=2)
    ax.plot([current_radio, current_radio], [0, bruta_t], color=color_punto, linestyle='-.', linewidth=1.5, zorder=4)
    ax.plot([0, current_radio], [bruta_t, bruta_t], color=color_punto, linestyle='-.', linewidth=1.5, zorder=4)

    # Estilos Radar / Cyber
    ax.grid(color='#1A1A1A', linestyle='--', linewidth=1, alpha=0.8)
    for s in ['top', 'right']: ax.spines[s].set_visible(False)
    for s in ['bottom', 'left']: ax.spines[s].set_color('#333333')

    ax.tick_params(colors='#666666', labelsize=8)
    ax.set_xlabel('RADIO DE OPERACIÓN [m]', color='#A0A0A0', fontsize=9, fontweight='bold', fontfamily='monospace')
    ax.set_ylabel('CAPACIDAD [Ton]', color='#A0A0A0', fontsize=9, fontweight='bold', fontfamily='monospace')
    ax.set_title('TELEMETRÍA LMI (ON-BOARD)', color='#FFFFFF', fontsize=12, fontweight='bold', fontfamily='monospace', loc='left', pad=15)

    # Caja de Datos Táctica
    box_props = dict(boxstyle='round,pad=0.5', facecolor='#111111', edgecolor=color_punto, alpha=0.9)
    ax.annotate(f"CARGA: {bruta_t:.1f}t\nRADIO: {current_radio}m\nMAX LMI: {cap_max_at_radio:.1f}t",
                (current_radio, bruta_t), textcoords="offset points", xytext=(15, 15),
                ha='left', color=color_punto, fontsize=9, fontweight='bold', fontfamily='monospace', bbox=box_props, zorder=6)

    ax.set_ylim(bottom=0)
    ax.set_xlim(left=0)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none', dpi=200)
    buf.seek(0)
    plt.close(fig)

    return buf.getvalue()
