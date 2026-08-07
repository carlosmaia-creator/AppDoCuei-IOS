import flet as ft
import sqlite3
import os
import traceback
from datetime import date, datetime, timedelta

# ==========================================
# CAMINHO ABSOLUTO E SEGURO DO BANCO DE DADOS
# ==========================================
try:
    PASTA_SEGURA = os.path.expanduser("~")
    teste = os.path.join(PASTA_SEGURA, ".teste_gravacao")
    with open(teste, "w") as f:
        pass
    os.remove(teste)
except Exception:
    PASTA_SEGURA = os.getcwd()

DB_PATH = os.path.join(PASTA_SEGURA, "life_os.db")

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""CREATE TABLE IF NOT EXISTS rotina_master (id INTEGER PRIMARY KEY AUTOINCREMENT, dia_semana TEXT, horario TEXT, atividade TEXT, descricao TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS execucao_rotina (id INTEGER PRIMARY KEY AUTOINCREMENT, rotina_id INTEGER, data TEXT, cumprido INTEGER DEFAULT 0, motivo TEXT, UNIQUE(rotina_id, data))""")
        c.execute("""CREATE TABLE IF NOT EXISTS ciclo_dia (data TEXT PRIMARY KEY, hora_inicio TEXT, hora_fim TEXT, status TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS gaps (id INTEGER PRIMARY KEY AUTOINCREMENT, horario TEXT, atividade TEXT, impacto TEXT, data TEXT)""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS excecoes (id INTEGER PRIMARY KEY AUTOINCREMENT, rotina TEXT, motivo TEXT, solucao TEXT, data TEXT, tipo_excecao TEXT, horario_real TEXT)""")
        try:
            c.execute("ALTER TABLE excecoes ADD COLUMN tipo_excecao TEXT DEFAULT '❌ Não Feito / Ignorado'")
            c.execute("ALTER TABLE excecoes ADD COLUMN horario_real TEXT DEFAULT ''")
        except sqlite3.OperationalError: pass

        c.execute("""CREATE TABLE IF NOT EXISTS refeicoes (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, foto_nome TEXT, data TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS agua_diaria (data TEXT PRIMARY KEY, copos INTEGER)""")
        c.execute("""CREATE TABLE IF NOT EXISTS financas (id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT, valor REAL, categoria TEXT, data TEXT, tipo TEXT)""")
        try:
            c.execute("ALTER TABLE financas ADD COLUMN tipo TEXT DEFAULT 'saida'")
        except sqlite3.OperationalError: pass

        c.execute("""CREATE TABLE IF NOT EXISTS config_financas (id INTEGER PRIMARY KEY, salario REAL, reserva REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS diario (id INTEGER PRIMARY KEY AUTOINCREMENT, vitoria TEXT, licao TEXT, desabafo TEXT, data TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS treinos_master (id INTEGER PRIMARY KEY AUTOINCREMENT, nome_treino TEXT, exercicios TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS historico_treinos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome_treino TEXT, duracao_min TEXT, detalhes_cargas TEXT, data TEXT)""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS gamificacao (id INTEGER PRIMARY KEY, xp INTEGER)""")
        c.execute("INSERT OR IGNORE INTO gamificacao (id, xp) VALUES (1, 0)")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro no init_db: {e}")

init_db()

def main(page: ft.Page):
    page.title = "Vida do Cuei"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = "#05070A" 

    try:
        data_hoje_iso = date.today().strftime("%Y-%m-%d")
        data_formatada = date.today().strftime("%d/%m/%Y")
        
        dias_pt = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
        dia_semana_hoje = dias_pt[date.today().weekday()]

        # ==========================================
        # DESIGN PREMIUM & GAMIFICAÇÃO
        # ==========================================
        def card_premium(content_ui, glow_color="#1F293D"):
            return ft.Container(
                content=content_ui,
                padding=15,
                border_radius=15,
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
                    colors=["#111621", "#090C13"]
                ),
                border=ft.border.all(1, ft.colors.with_opacity(0.4, glow_color)),
                shadow=ft.BoxShadow(
                    spread_radius=1, blur_radius=10, 
                    color=ft.colors.with_opacity(0.15, glow_color),
                    offset=ft.Offset(0, 4)
                )
            )

        def cabecalho(titulo, subtitulo, cor="#00F2FE"):
            return ft.Column([
                ft.Text(titulo.upper(), size=18, weight=ft.FontWeight.BOLD, color=cor),
                ft.Text(subtitulo, size=11, color="#9CA3AF"),
            ], spacing=2)

        lbl_level = ft.Text("👑 NÍVEL 1", size=14, weight=ft.FontWeight.BOLD, color="#FFD700")
        pb_xp = ft.ProgressBar(value=0, color="#FFD700", bgcolor="#1F293D", height=8)
        lbl_xp_text = ft.Text("0/100 XP", size=10, color="#9CA3AF")

        def get_xp():
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT xp FROM gamificacao WHERE id = 1")
                row = c.fetchone()
                conn.close()
                return row[0] if row else 0
            except:
                return 0

        def set_xp(val):
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("UPDATE gamificacao SET xp = ? WHERE id = 1", (val,))
                conn.commit()
                conn.close()
            except: pass

        def atualizar_header_xp():
            xp_total = get_xp()
            if xp_total < 0:
                set_xp(0)
                xp_total = 0
            nivel = (xp_total // 100) + 1
            xp_atual = xp_total % 100
            
            lbl_level.value = f"👑 NÍVEL {nivel}"
            pb_xp.value = xp_atual / 100
            lbl_xp_text.value = f"{xp_atual} / 100 XP para o Nível {nivel+1}"
            page.update()

        def add_xp(pontos):
            xp_total = get_xp()
            novo_xp = xp_total + pontos
            set_xp(novo_xp)
            atualizar_header_xp()

        painel_gamificacao = ft.Container(
            content=ft.Column([
                ft.Row([lbl_level, lbl_xp_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                pb_xp
            ], spacing=5),
            padding=15, bgcolor="#0B0E14", border=ft.border.only(bottom=ft.border.BorderSide(1, "#1F293D"))
        )

        # ==========================================
        # ABA 1: ROTINA
        # ==========================================
        dd_dia_semana_cadastro = ft.Dropdown(
            label="Dia da Semana para esta Rotina", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"),
            options=[ft.dropdown.Option(d) for d in dias_pt]
        )
        txt_horario = ft.TextField(label="Horário (Ex: 08:00 - 12:00)", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        txt_atividade = ft.TextField(label="Nome da Atividade / Tarefa", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        txt_descricao = ft.TextField(label="Descrição Breve", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))

        painel_status_dia = ft.Column(spacing=10)
        lista_rotina_hoje_ui = ft.Column(spacing=15)
        lista_outros_dias_ui = ft.Column(spacing=10)
        dd_excecoes_rotina = ft.Dropdown(
            label="Qual meta ou rotina falhou?",
            border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF")
        )

        def salvar_rotina_master(e):
            if dd_dia_semana_cadastro.value and txt_horario.value and txt_atividade.value:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO rotina_master (dia_semana, horario, atividade, descricao) VALUES (?, ?, ?, ?)",
                          (dd_dia_semana_cadastro.value, txt_horario.value, txt_atividade.value, txt_descricao.value or ""))
                conn.commit()
                conn.close()
                txt_horario.value = ""
                txt_atividade.value = ""
                txt_descricao.value = ""
                carregar_rotina_do_dia()

        def abrir_modal_dia(dia_nome):
            conteudo_modal = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
            def recarregar_modal():
                conteudo_modal.controls.clear()
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT id, horario, atividade, descricao FROM rotina_master WHERE dia_semana = ?", (dia_nome,))
                tarefas = c.fetchall()
                conn.close()

                if not tarefas:
                    conteudo_modal.controls.append(ft.Text("Nenhuma tarefa cadastrada.", size=11, color="#9CA3AF"))

                for id_o, h_o, at_o, desc_o in tarefas:
                    tf_hor_edit = ft.TextField(value=h_o, label="Horário", border_color="#1F293D", color="#FFFFFF", text_size=11, width=110)
                    tf_desc_edit = ft.TextField(value=desc_o or "", label="Descrição", border_color="#1F293D", color="#FFFFFF", text_size=11, expand=True)

                    def deletar_item(e, item_id=id_o):
                        cn = sqlite3.connect(DB_PATH)
                        cur = cn.cursor()
                        cur.execute("DELETE FROM rotina_master WHERE id = ?", (item_id,))
                        cur.execute("DELETE FROM execucao_rotina WHERE rotina_id = ?", (item_id,))
                        cn.commit()
                        cn.close()
                        recarregar_modal()
                        carregar_rotina_do_dia()

                    def salvar_item(e, item_id=id_o, tf_h=tf_hor_edit, tf_d=tf_desc_edit):
                        cn = sqlite3.connect(DB_PATH)
                        cur = cn.cursor()
                        cur.execute("UPDATE rotina_master SET horario = ?, descricao = ? WHERE id = ?", (tf_h.value, tf_d.value, item_id))
                        cn.commit()
                        cn.close()
                        recarregar_modal()
                        carregar_rotina_do_dia()

                    conteudo_modal.controls.append(
                        card_premium(
                            ft.Column([
                                ft.Row([
                                    ft.Text(f"• {at_o}", size=13, weight=ft.FontWeight.BOLD, color="#FFFFFF", expand=True),
                                    ft.IconButton(icon=ft.icons.DELETE, icon_color="#EF4444", icon_size=18, tooltip="Apagar tarefa", on_click=deletar_item)
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Row([
                                    tf_hor_edit, tf_desc_edit,
                                    ft.IconButton(icon=ft.icons.SAVE, icon_color="#10B981", icon_size=20, tooltip="Salvar alteração", on_click=salvar_item)
                                ], spacing=6)
                            ]), glow_color="#3B82F6"
                        )
                    )
                bs.update()

            def fechar_bs(e):
                bs.open = False
                bs.update()

            bs = ft.BottomSheet(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"📌 TAREFAS DE {dia_nome.upper()}", size=14, weight=ft.FontWeight.BOLD, color="#00F2FE"),
                            ft.IconButton(icon=ft.icons.CLOSE, icon_color="#9CA3AF", on_click=fechar_bs)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(color="#1F293D", height=10),
                        conteudo_modal
                    ], spacing=10, expand=True),
                    padding=20, bgcolor="#131927", border_radius=ft.border_radius.only(top_left=15, top_right=15), height=550
                )
            )
            page.overlay.append(bs)
            bs.open = True
            page.update()
            recarregar_modal()

        def carregar_rotina_do_dia():
            try:
                painel_status_dia.controls.clear()
                lista_rotina_hoje_ui.controls.clear()
                lista_outros_dias_ui.controls.clear()
                dd_excecoes_rotina.options.clear()

                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()

                c.execute("SELECT hora_inicio, hora_fim, status FROM ciclo_dia WHERE data = ?", (data_formatada,))
                ciclo = c.fetchone()

                status_ciclo = ciclo[2] if ciclo else "NAO_INICIADO"
                h_ini = ciclo[0] if ciclo else "--:--"
                h_fim = ciclo[1] if ciclo else "--:--"

                def iniciar_dia_action(ev):
                    now_str = datetime.now().strftime("%H:%M")
                    cn = sqlite3.connect(DB_PATH)
                    cur = cn.cursor()
                    cur.execute("INSERT OR REPLACE INTO ciclo_dia (data, hora_inicio, status) VALUES (?, ?, ?)",
                                (data_formatada, now_str, "EM_ANDAMENTO"))
                    cn.commit()
                    cn.close()
                    carregar_rotina_do_dia()

                def concluir_dia_action(ev):
                    now_str = datetime.now().strftime("%H:%M")
                    cn = sqlite3.connect(DB_PATH)
                    cur = cn.cursor()
                    cur.execute("UPDATE ciclo_dia SET hora_fim = ?, status = ? WHERE data = ?",
                                (now_str, "CONCLUIDO", data_formatada))
                    cn.commit()
                    cn.close()
                    add_xp(50) 
                    carregar_rotina_do_dia()

                def desfazer_ciclo_action(ev):
                    cn = sqlite3.connect(DB_PATH)
                    cur = cn.cursor()
                    if status_ciclo == "CONCLUIDO":
                        cur.execute("UPDATE ciclo_dia SET status = ? WHERE data = ?", ("EM_ANDAMENTO", data_formatada))
                    else:
                        cur.execute("DELETE FROM ciclo_dia WHERE data = ?", (data_formatada,))
                    cn.commit()
                    cn.close()
                    carregar_rotina_do_dia()

                if status_ciclo == "NAO_INICIADO":
                    painel_status_dia.controls.append(
                        card_premium(
                            ft.Column([
                                ft.Text(f"📅 HOJE É: {dia_semana_hoje.upper()} ({data_formatada})", size=13, weight=ft.FontWeight.BOLD, color="#00F2FE"),
                                ft.Text("Seu dia ainda não foi iniciado. Clique abaixo para começar!", size=11, color="#9CA3AF"),
                                ft.ElevatedButton("☀️ INICIAR O DIA", bgcolor="#00F2FE", color="#000000", height=45, on_click=iniciar_dia_action)
                            ]), glow_color="#00F2FE"
                        )
                    )
                elif status_ciclo == "EM_ANDAMENTO":
                    painel_status_dia.controls.append(
                        card_premium(
                            ft.Column([
                                ft.Row([
                                    ft.Text(f"☀️ DIA EM ANDAMENTO ({dia_semana_hoje})", size=12, weight=ft.FontWeight.BOLD, color="#10B981"),
                                    ft.Text(f"Iniciado às: {h_ini}", size=11, color="#9CA3AF")
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Row([
                                    ft.ElevatedButton("🌙 CONCLUIR O DIA", bgcolor="#8B5CF6", color="#FFFFFF", height=40, expand=True, on_click=concluir_dia_action),
                                    ft.ElevatedButton("↩️ Cancelar Início", bgcolor="#1F293D", color="#EF4444", height=40, on_click=desfazer_ciclo_action)
                                ], spacing=8)
                            ]), glow_color="#10B981"
                        )
                    )
                else:
                    painel_status_dia.controls.append(
                        card_premium(
                            ft.Column([
                                ft.Row([
                                    ft.Text(f"🌙 DIA CONCLUÍDO! ({dia_semana_hoje})", size=13, weight=ft.FontWeight.BOLD, color="#EC4899"),
                                    ft.Text(f"Início: {h_ini} | Fim: {h_fim}", size=10, color="#9CA3AF")
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.ElevatedButton("↩️ Retomar Dia (Desfazer Conclusão)", bgcolor="#1F293D", color="#00F2FE", height=38, on_click=desfazer_ciclo_action)
                            ]), glow_color="#EC4899"
                        )
                    )

                c.execute("SELECT id, horario, atividade, descricao FROM rotina_master WHERE dia_semana = ?", (dia_semana_hoje,))
                rotinas_hoje = c.fetchall()

                if not rotinas_hoje:
                    lista_rotina_hoje_ui.controls.append(ft.Text(f"Nenhuma rotina cadastrada para {dia_semana_hoje}. Cadastre abaixo!", size=11, color="#9CA3AF"))

                for id_rot, hor, ativ, desc in rotinas_hoje:
                    dd_excecoes_rotina.options.append(ft.dropdown.Option(ativ))
                    
                    c.execute("SELECT cumprido, motivo FROM execucao_rotina WHERE rotina_id = ? AND data = ?", (id_rot, data_hoje_iso))
                    exec_hoje = c.fetchone()
                    cumprido_hoje = bool(exec_hoje[0]) if exec_hoje else False
                    motivo_hoje = exec_hoje[1] if exec_hoje else ""

                    c.execute("SELECT tipo_excecao, horario_real FROM excecoes WHERE rotina = ? AND data = ?", (ativ, data_formatada))
                    exc_registrada = c.fetchone()

                    alerta_ui = ft.Container()
                    cor_card = "#00F2FE"
                    if exc_registrada:
                        t_exc, h_real = exc_registrada
                        if "Atraso" in str(t_exc):
                            cor_card = "#F59E0B"
                            alerta_ui = ft.Container(
                                content=ft.Text(f"⚠️ {t_exc} | Real: {h_real}", size=10, weight=ft.FontWeight.BOLD, color="#F59E0B"),
                                padding=5, bgcolor="#451A03", border_radius=5
                            )
                        else:
                            cor_card = "#EF4444"
                            alerta_ui = ft.Container(
                                content=ft.Text(f"❌ {t_exc}", size=10, weight=ft.FontWeight.BOLD, color="#EF4444"),
                                padding=5, bgcolor="#450a0a", border_radius=5
                            )

                    if cumprido_hoje and cor_card == "#00F2FE":
                        cor_card = "#10B981"

                    txt_motivo = ft.TextField(value=motivo_hoje, hint_text="Observação Rápida", border_color="#1F293D", color="#FFFFFF", text_size=11)

                    def deletar_rotina(e, id_item=id_rot):
                        cn = sqlite3.connect(DB_PATH)
                        cur = cn.cursor()
                        cur.execute("DELETE FROM rotina_master WHERE id = ?", (id_item,))
                        cur.execute("DELETE FROM execucao_rotina WHERE rotina_id = ?", (id_item,))
                        cn.commit()
                        cn.close()
                        carregar_rotina_do_dia()

                    def salvar_motivo(e, id_item=id_rot, campo_m=txt_motivo):
                        cn = sqlite3.connect(DB_PATH)
                        cur = cn.cursor()
                        cur.execute("INSERT INTO execucao_rotina (rotina_id, data, motivo) VALUES (?, ?, ?) ON CONFLICT(rotina_id, data) DO UPDATE SET motivo = excluded.motivo", (id_item, data_hoje_iso, campo_m.value))
                        cn.commit()
                        cn.close()

                    def alternar_check(e, id_item=id_rot):
                        val = 1 if e.control.value else 0
                        if val == 1: add_xp(10)
                        else: add_xp(-10)

                        cn = sqlite3.connect(DB_PATH)
                        cur = cn.cursor()
                        cur.execute("INSERT INTO execucao_rotina (rotina_id, data, cumprido) VALUES (?, ?, ?) ON CONFLICT(rotina_id, data) DO UPDATE SET cumprido = excluded.cumprido", (id_item, data_hoje_iso, val))
                        cn.commit()
                        cn.close()
                        carregar_rotina_do_dia()

                    lista_rotina_hoje_ui.controls.append(
                        card_premium(
                            ft.Column([
                                ft.Row([
                                    ft.Container(content=ft.Text(hor, size=10, color="#000000", weight=ft.FontWeight.BOLD), bgcolor=cor_card, padding=4, border_radius=4),
                                    ft.Text(ativ, size=14, weight=ft.FontWeight.BOLD, color="#FFFFFF", expand=True),
                                    ft.IconButton(icon=ft.icons.DELETE, icon_color="#EF4444", tooltip="Apagar", on_click=deletar_rotina)
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Text(f"Detalhes: {desc}", size=11, color="#9CA3AF") if desc else ft.Container(),
                                alerta_ui,
                                txt_motivo,
                                ft.Row([
                                    ft.ElevatedButton("Salvar Obs", bgcolor="#1F293D", color="#FFFFFF", height=30, on_click=salvar_motivo),
                                    ft.Checkbox(label="Concluído", value=cumprido_hoje, on_change=alternar_check, fill_color="#10B981")
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                            ]), glow_color=cor_card
                        )
                    )

                for d_nome in dias_pt:
                    if d_nome != dia_semana_hoje:
                        c.execute("SELECT COUNT(*) FROM rotina_master WHERE dia_semana = ?", (d_nome,))
                        qtd_tarefas = c.fetchone()[0]

                        def criar_evento_click(nome_d=d_nome):
                            return lambda e: abrir_modal_dia(nome_d)

                        lista_outros_dias_ui.controls.append(
                            card_premium(
                                ft.Container(
                                    content=ft.Row([
                                        ft.Column([
                                            ft.Text(f"📌 {d_nome.upper()}", size=12, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                                            ft.Text(f"{qtd_tarefas} tarefa(s) cadastrada(s)", size=10, color="#9CA3AF")
                                        ], expand=True),
                                        ft.Text("Gerenciar 🔍", size=11, color="#00F2FE", weight=ft.FontWeight.BOLD)
                                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                    on_click=criar_evento_click(d_nome)
                                ), glow_color="#3B82F6"
                            )
                        )

                conn.close()
                page.update()
            except Exception as ex:
                print(f"Erro em carregar_rotina_do_dia: {ex}")

        view_rotina = ft.Container(
            content=ft.Column([
                cabecalho("1. Engenharia da Rotina", f"Rotina Inteligente • {dia_semana_hoje}"),
                painel_status_dia,
                ft.Divider(color="#1F293D", height=10),
                ft.Text(f"PROGRAMAÇÃO DE HOJE ({dia_semana_hoje.upper()})", size=12, weight=ft.FontWeight.BOLD, color="#00F2FE"),
                lista_rotina_hoje_ui,
                ft.Divider(color="#1F293D", height=10),
                ft.Text("OUTROS DIAS DA SEMANA (CLIQUE PARA VER/EDITAR)", size=12, weight=ft.FontWeight.BOLD, color="#3B82F6"),
                lista_outros_dias_ui,
                ft.Divider(color="#1F293D", height=10),
                card_premium(
                    ft.Column([
                        ft.Text("CONFIGURAR ROTINA POR DIA", size=11, weight=ft.FontWeight.BOLD, color="#9CA3AF"),
                        dd_dia_semana_cadastro, txt_horario, txt_atividade, txt_descricao,
                        ft.ElevatedButton("CADASTRAR NESTE DIA", bgcolor="#1F293D", color="#FFFFFF", height=40, on_click=salvar_rotina_master)
                    ], spacing=8), glow_color="#1F293D"
                )
            ], spacing=12, scroll=ft.ScrollMode.AUTO),
            padding=15, expand=True
        )

        # ==========================================
        # ABA 2: TEMPO LIVRE & GAPS
        # ==========================================
        lista_gaps_ui = ft.Column(spacing=10)

        def carregar_gaps():
            try:
                lista_gaps_ui.controls.clear()
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT id, horario, atividade, impacto FROM gaps ORDER BY id DESC")
                rows = c.fetchall()
                conn.close()

                for gap_id, hor, ativ, imp in rows:
                    cor_gap = "#10B981"
                    if "🔴" in imp: cor_gap = "#EF4444"
                    elif "🟡" in imp: cor_gap = "#F59E0B"
                    elif "🔵" in imp: cor_gap = "#3B82F6"
                    elif "🏃" in imp: cor_gap = "#8B5CF6"
                    elif "🤝" in imp: cor_gap = "#EC4899"
                    elif "💼" in imp: cor_gap = "#00F2FE"

                    def deletar_gap(e, id_item=gap_id):
                        conn = sqlite3.connect(DB_PATH)
                        cur = conn.cursor()
                        cur.execute("DELETE FROM gaps WHERE id = ?", (id_item,))
                        conn.commit()
                        conn.close()
                        carregar_gaps()
                        carregar_resumo_dia()

                    lista_gaps_ui.controls.append(
                        card_premium(
                            ft.Row([
                                ft.Column([
                                    ft.Text(f"Janela: {hor}", size=12, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                                    ft.Text(ativ, size=11, color="#9CA3AF")
                                ], expand=True),
                                ft.Text(imp, size=11, color=cor_gap, weight=ft.FontWeight.BOLD),
                                ft.IconButton(icon=ft.icons.DELETE, icon_color="#EF4444", tooltip="Apagar Gap", on_click=deletar_gap)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), glow_color=cor_gap
                        )
                    )
                page.update()
            except: pass

        gap_horario = ft.TextField(label="Janela de Horário", hint_text="Ex: 19:00 às 19:30", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        gap_atividade = ft.TextField(label="Atividade Realizada", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        
        gap_impacto = ft.Dropdown(
            label="Classificação do Impacto", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"),
            options=[
                ft.dropdown.Option("🔴 Desperdício / Procrastinação"),
                ft.dropdown.Option("🟡 Descanso / Recuperação"),
                ft.dropdown.Option("🟢 Estudo / Conhecimento"),
                ft.dropdown.Option("🔵 Manutenção da Vida (Casa, Mercado, etc)"),
                ft.dropdown.Option("🏃 Saúde / Bem-estar"),
                ft.dropdown.Option("🤝 Social / Família / Relacionamentos"),
                ft.dropdown.Option("💼 Trabalho / Burocracia"),
            ]
        )

        def salvar_gap(e):
            if gap_horario.value and gap_atividade.value and gap_impacto.value:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO gaps (horario, atividade, impacto, data) VALUES (?, ?, ?, ?)",
                          (gap_horario.value, gap_atividade.value, gap_impacto.value, data_formatada))
                conn.commit()
                conn.close()
                add_xp(5) 
                gap_horario.value = ""
                gap_atividade.value = ""
                carregar_gaps()
                carregar_resumo_dia()

        view_gaps = ft.Container(
            content=ft.Column([
                cabecalho("2. Rastreio de Tempo Livre", "Mapeie seus intervalos e desperdícios", "#F59E0B"),
                gap_horario, gap_atividade, gap_impacto,
                ft.ElevatedButton("REGISTRAR USO DO TEMPO", bgcolor="#F59E0B", color="#000000", height=45, on_click=salvar_gap),
                ft.Text("GAPS RECENTES REGISTRADOS", size=12, weight=ft.FontWeight.BOLD, color="#9CA3AF"),
                lista_gaps_ui
            ], spacing=12, scroll=ft.ScrollMode.AUTO),
            padding=15, expand=True
        )

        # ==========================================
        # ABA 3: DIÁRIO DE EXCEÇÕES
        # ==========================================
        lista_excecoes_ui = ft.Column(spacing=10)

        def carregar_excecoes():
            try:
                lista_excecoes_ui.controls.clear()
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT id, rotina, motivo, solucao, data, tipo_excecao, horario_real FROM excecoes ORDER BY id DESC")
                rows = c.fetchall()
                conn.close()

                for exc_id, rot, mot, sol, dt, t_exc, h_real in rows:
                    def deletar_excecao(e, id_item=exc_id):
                        conn = sqlite3.connect(DB_PATH)
                        cur = conn.cursor()
                        cur.execute("DELETE FROM excecoes WHERE id = ?", (id_item,))
                        conn.commit()
                        conn.close()
                        carregar_excecoes()
                        carregar_rotina_do_dia()
                        carregar_resumo_dia()

                    cor_borda = "#F59E0B" if "Atraso" in str(t_exc) else "#EF4444"

                    lista_excecoes_ui.controls.append(
                        card_premium(
                            ft.Column([
                                ft.Row([
                                    ft.Text(f"Erro em: {rot}", size=13, weight=ft.FontWeight.BOLD, color=cor_borda),
                                    ft.Text(dt or "", size=10, color="#6B7280"),
                                    ft.IconButton(icon=ft.icons.DELETE, icon_color="#EF4444", tooltip="Apagar", on_click=deletar_excecao)
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Text(f"Classificação: {t_exc} " + (f"(Realizado: {h_real})" if h_real else ""), size=11, color="#FFFFFF", weight=ft.FontWeight.BOLD),
                                ft.Text(f"Motivo: {mot}", size=11, color="#9CA3AF"),
                                ft.Text(f"Plano de Ação: {sol}", size=11, color="#10B981") if sol else ft.Container()
                            ]), glow_color=cor_borda
                        )
                    )
                page.update()
            except: pass

        dd_tipo_excecao = ft.Dropdown(
            label="Tipo de Falha", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"),
            options=[
                ft.dropdown.Option("⚠️ Atraso / Mudança de Horário"),
                ft.dropdown.Option("❌ Não Feito / Ignorado")
            ]
        )
        exc_horario_real = ft.TextField(label="Horário Real (Ex: 21:30 às 23:00)", hint_text="Deixe em branco se não foi feito", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        exc_motivo = ft.TextField(label="Motivo do Descumprimento / Atraso", multiline=True, border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        exc_solucao = ft.TextField(label="O que fará para EVITAR esse erro amanhã?", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))

        def salvar_excecao(e):
            if dd_excecoes_rotina.value and exc_motivo.value and dd_tipo_excecao.value:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO excecoes (rotina, motivo, solucao, data, tipo_excecao, horario_real) VALUES (?, ?, ?, ?, ?, ?)",
                          (dd_excecoes_rotina.value, exc_motivo.value, exc_solucao.value or "", data_formatada, dd_tipo_excecao.value, exc_horario_real.value or ""))
                conn.commit()
                conn.close()
                
                if "Não Feito" in dd_tipo_excecao.value:
                    add_xp(-10)
                
                exc_motivo.value = ""
                exc_solucao.value = ""
                exc_horario_real.value = ""
                carregar_excecoes()
                carregar_rotina_do_dia()
                carregar_resumo_dia()

        view_excecoes = ft.Container(
            content=ft.Column([
                cabecalho("3. Diário de Exceções", "Auditoria de não-conformidade (Puxado da sua Rotina)", "#EF4444"),
                dd_excecoes_rotina, dd_tipo_excecao, exc_horario_real, exc_motivo, exc_solucao,
                ft.ElevatedButton("SALVAR FALHA / ATRASO", bgcolor="#EF4444", color="#FFFFFF", height=45, on_click=salvar_excecao),
                ft.Text("HISTÓRICO DE EXCEÇÕES", size=12, weight=ft.FontWeight.BOLD, color="#9CA3AF"),
                lista_excecoes_ui
            ], spacing=12, scroll=ft.ScrollMode.AUTO),
            padding=15, expand=True
        )

        # ==========================================
        # ABA 4: SAÚDE & CORPO
        # ==========================================
        res_agua = None
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT copos FROM agua_diaria WHERE data = ?", (data_formatada,))
            res_agua = c.fetchone()
            conn.close()
        except: pass
        
        contador_agua = [res_agua[0] if res_agua else 0]
        agua_meta_xp_ganho = [False]
        
        if contador_agua[0] >= 12:
            agua_meta_xp_ganho[0] = True

        copos_agua = ft.Text("", size=14, weight=ft.FontWeight.BOLD, color="#FFFFFF")

        def salvar_agua_db():
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO agua_diaria (data, copos) VALUES (?, ?)", (data_formatada, contador_agua[0]))
                conn.commit()
                conn.close()
                carregar_resumo_dia()
            except: pass

        def atualizar_texto_agua():
            litros = contador_agua[0] * 0.25
            if litros >= 3.0:
                copos_agua.value = f"✅ {contador_agua[0]} Copos ({litros:.2f}L / 3.00L)"
                copos_agua.color = "#10B981"
            else:
                copos_agua.value = f"💧 {contador_agua[0]} Copos ({litros:.2f}L / 3.00L)"
                copos_agua.color = "#FFFFFF"
            page.update()

        def add_agua(e):
            contador_agua[0] += 1
            if contador_agua[0] == 12 and not agua_meta_xp_ganho[0]:
                add_xp(20)
                agua_meta_xp_ganho[0] = True
            salvar_agua_db()
            atualizar_texto_agua()

        def rem_agua(e):
            if contador_agua[0] > 0:
                contador_agua[0] -= 1
                salvar_agua_db()
                atualizar_texto_agua()

        def zerar_agua(e):
            contador_agua[0] = 0
            salvar_agua_db()
            atualizar_texto_agua()
            
        atualizar_texto_agua()

        lbl_foto = ft.Text("Nenhuma foto selecionada", size=11, color="#9CA3AF")
        foto_path = [""]
        
        def foto_selecionada(e: ft.FilePickerResultEvent):
            if e.files:
                foto_path[0] = e.files[0].name
                lbl_foto.value = f"Foto anexada: {e.files[0].name}"
                page.update()

        file_picker = ft.FilePicker(on_result=foto_selecionada)
        page.overlay.append(file_picker)

        dd_tipo_refeicao = ft.Dropdown(
            label="Qual foi a Refeição?", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"),
            options=[
                ft.dropdown.Option("☕ Café da Manhã"),
                ft.dropdown.Option("🍲 Almoço"),
                ft.dropdown.Option("🍎 Lanche / Café da Tarde"),
                ft.dropdown.Option("🍽️ Jantar"),
                ft.dropdown.Option("🌙 Ceia / Lanche da Noite"),
            ]
        )
        txt_desc_refeicao = ft.TextField(label="O que você comeu?", hint_text="Ex: Arroz, feijão, frango e salada", multiline=True, border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        lista_refeicoes_ui = ft.Column(spacing=10)

        def carregar_refeicoes():
            try:
                lista_refeicoes_ui.controls.clear()
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT id, tipo, descricao, foto_nome, data FROM refeicoes ORDER BY id DESC")
                rows = c.fetchall()
                conn.close()

                for ref_id, tip, desc, ft_nom, dt in rows:
                    def deletar_refeicao(e, id_item=ref_id):
                        conn = sqlite3.connect(DB_PATH)
                        cur = conn.cursor()
                        cur.execute("DELETE FROM refeicoes WHERE id = ?", (id_item,))
                        conn.commit()
                        conn.close()
                        carregar_refeicoes()
                        carregar_resumo_dia()

                    lista_refeicoes_ui.controls.append(
                        card_premium(
                            ft.Column([
                                ft.Row([
                                    ft.Text(tip, size=13, weight=ft.FontWeight.BOLD, color="#10B981"),
                                    ft.Text(dt or "", size=10, color="#6B7280"),
                                    ft.IconButton(icon=ft.icons.DELETE, icon_color="#EF4444", tooltip="Apagar", on_click=deletar_refeicao)
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Text(f"Prato: {desc}", size=11, color="#FFFFFF"),
                                ft.Text(f"📸 {ft_nom}", size=10, color="#3B82F6") if ft_nom else ft.Container()
                            ]), glow_color="#10B981"
                        )
                    )
                page.update()
            except: pass

        def salvar_refeicao(e):
            if dd_tipo_refeicao.value and txt_desc_refeicao.value:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO refeicoes (tipo, descricao, foto_nome, data) VALUES (?, ?, ?, ?)",
                          (dd_tipo_refeicao.value, txt_desc_refeicao.value, foto_path[0], data_formatada))
                conn.commit()
                conn.close()
                txt_desc_refeicao.value = ""
                lbl_foto.value = "Nenhuma foto selecionada"
                foto_path[0] = ""
                add_xp(5)
                carregar_refeicoes()
                carregar_resumo_dia()

        view_nutricao = ft.Container(
            content=ft.Column([
                cabecalho("4. Engenharia Corporal", "Registro real de hidratação, refeição e treino", "#10B981"),
                card_premium(
                    ft.Column([
                        ft.Row([ft.Text("META DIÁRIA: 3 LITROS (12 COPOS)", size=12, color="#9CA3AF", weight=ft.FontWeight.BOLD), copos_agua], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Row([
                            ft.ElevatedButton("- 1 Copo", bgcolor="#EF4444", color="#FFFFFF", on_click=rem_agua, expand=True),
                            ft.ElevatedButton("+ 1 Copo", bgcolor="#3B82F6", color="#FFFFFF", on_click=add_agua, expand=True),
                            ft.ElevatedButton("Zerar", bgcolor="#1F293D", color="#FFFFFF", on_click=zerar_agua),
                        ], spacing=8)
                    ]), glow_color="#3B82F6"
                ),
                ft.Text("REGISTRAR REFEIÇÃO DO DIA", size=12, weight=ft.FontWeight.BOLD, color="#10B981"),
                dd_tipo_refeicao, txt_desc_refeicao,
                ft.ElevatedButton("Anexar Foto da Refeição 📸", bgcolor="#1F293D", color="#FFFFFF", on_click=lambda _: file_picker.pick_files(allow_multiple=False)),
                lbl_foto,
                ft.ElevatedButton("REGISTRAR REFEIÇÃO", bgcolor="#10B981", color="#000000", height=45, on_click=salvar_refeicao),
                ft.Text("REFEIÇÕES LANÇADAS", size=12, weight=ft.FontWeight.BOLD, color="#9CA3AF"),
                lista_refeicoes_ui
            ], spacing=12, scroll=ft.ScrollMode.AUTO),
            padding=15, expand=True
        )

        # ==========================================
        # ABA 5: COFRE & FINANÇAS
        # ==========================================
        txt_salario = ft.TextField(label="Salário Mensal (R$)", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        txt_reserva = ft.TextField(label="Reserva Desejada (R$)", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        lbl_saldo_disponivel = ft.Text("R$ 0,00", size=26, weight=ft.FontWeight.BOLD, color="#FFFFFF")
        lista_compras_ui = ft.Column(spacing=5)

        def atualizar_financeiro():
            try:
                lista_compras_ui.controls.clear()
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT salario, reserva FROM config_financas WHERE id = 1")
                cfg = c.fetchone()
                salario = cfg[0] if cfg else 0.0
                reserva = cfg[1] if cfg else 0.0

                c.execute("SELECT id, descricao, valor, categoria, tipo FROM financas ORDER BY id DESC")
                transacoes = c.fetchall()
                conn.close()

                total_gastos = sum(val for _, _, val, _, t in transacoes if t == 'saida')
                total_entradas = sum(val for _, _, val, _, t in transacoes if t == 'entrada')
                
                saldo_livre = (salario - reserva) + total_entradas - total_gastos
                lbl_saldo_disponivel.value = f"R$ {saldo_livre:,.2f}"

                for comp_id, desc, val, cat, tipo_t in transacoes:
                    sinal = "+" if tipo_t == "entrada" else "-"
                    cor_valor = "#10B981" if tipo_t == "entrada" else "#EF4444"
                    
                    def deletar_compra(e, id_item=comp_id):
                        conn = sqlite3.connect(DB_PATH)
                        cur = conn.cursor()
                        cur.execute("DELETE FROM financas WHERE id = ?", (id_item,))
                        conn.commit()
                        conn.close()
                        atualizar_financeiro()
                        carregar_resumo_dia()

                    lista_compras_ui.controls.append(
                        card_premium(
                            ft.Row([
                                ft.Column([
                                    ft.Text(desc, size=12, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                                    ft.Text(cat, size=10, color="#9CA3AF")
                                ], expand=True),
                                ft.Text(f"{sinal} R$ {val:,.2f}", size=12, color=cor_valor, weight=ft.FontWeight.BOLD),
                                ft.IconButton(icon=ft.icons.DELETE, icon_color="#EF4444", tooltip="Apagar", on_click=deletar_compra)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), glow_color=cor_valor
                        )
                    )
                page.update()
            except: pass

        def salvar_config_salario(e):
            if txt_salario.value:
                sal = float(txt_salario.value.replace(",", "."))
                res = float(txt_reserva.value.replace(",", ".")) if txt_reserva.value else 0.0
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO config_financas (id, salario, reserva) VALUES (1, ?, ?)", (sal, res))
                conn.commit()
                conn.close()
                atualizar_financeiro()
                carregar_resumo_dia()

        dd_tipo_transacao = ft.Dropdown(
            label="Tipo de Lançamento", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"),
            value="saida",
            options=[
                ft.dropdown.Option(key="saida", text="🔴 Saída (Gasto / Despesa)"),
                ft.dropdown.Option(key="entrada", text="🟢 Entrada (Receita Extra / Pix)"),
            ]
        )
        fin_valor = ft.TextField(label="Valor (R$)", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        fin_desc = ft.TextField(label="Descrição", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        fin_cat = ft.Dropdown(
            label="Categoria", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"),
            options=[
                ft.dropdown.Option("💰 Renda Extra / Pix / Vendas"),
                ft.dropdown.Option("🛒 Alimentação / Mercado"),
                ft.dropdown.Option("🍔 Lanche / Restaurantes"),
                ft.dropdown.Option("⛽ Transporte / Combustível"),
                ft.dropdown.Option("🏠 Moradia / Aluguel / Contas"),
                ft.dropdown.Option("💊 Saúde / Farmácia / Academia"),
                ft.dropdown.Option("🍿 Lazer / Entretenimento"),
                ft.dropdown.Option("👕 Vestuário / Compras"),
                ft.dropdown.Option("💻 Tecnologia / Assinaturas"),
                ft.dropdown.Option("💳 Cartão / Boletos"),
                ft.dropdown.Option("❓ Outros / Diversos"),
            ]
        )

        def lancar_transacao(e):
            if fin_valor.value and fin_desc.value and dd_tipo_transacao.value:
                v = float(fin_valor.value.replace(",", "."))
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO financas (descricao, valor, categoria, data, tipo) VALUES (?, ?, ?, ?, ?)",
                          (fin_desc.value, v, fin_cat.value or "Outros", data_formatada, dd_tipo_transacao.value))
                conn.commit()
                conn.close()
                fin_valor.value = ""
                fin_desc.value = ""
                add_xp(5)
                atualizar_financeiro()
                carregar_resumo_dia()

        view_financas = ft.Container(
            content=ft.Column([
                cabecalho("5. Gestão Patrimonial", "Defina seu salário e monitore a queda do saldo", "#8B5CF6"),
                card_premium(
                    ft.Column([
                        ft.Text("CONFIGURAR RENDA FIXA", size=11, color="#8B5CF6", weight=ft.FontWeight.BOLD),
                        txt_salario, txt_reserva,
                        ft.ElevatedButton("Salvar Renda", bgcolor="#8B5CF6", color="#FFFFFF", on_click=salvar_config_salario)
                    ], spacing=8), glow_color="#1F293D"
                ),
                card_premium(
                    ft.Column([
                        ft.Text("SALDO DISPONÍVEL (SALÁRIO + EXTRAS - GASTOS)", size=10, color="#9CA3AF"),
                        lbl_saldo_disponivel,
                    ]), glow_color="#8B5CF6"
                ),
                ft.Divider(color="#1F293D", height=10),
                ft.Text("NOVA MOVIMENTAÇÃO", size=12, weight=ft.FontWeight.BOLD, color="#9CA3AF"),
                dd_tipo_transacao, fin_valor, fin_desc, fin_cat,
                ft.ElevatedButton("LANÇAR MOVIMENTAÇÃO", bgcolor="#8B5CF6", color="#FFFFFF", height=45, on_click=lancar_transacao),
                ft.Text("HISTÓRICO DO COFRE", size=12, weight=ft.FontWeight.BOLD, color="#9CA3AF"),
                lista_compras_ui
            ], spacing=12, scroll=ft.ScrollMode.AUTO),
            padding=15, expand=True
        )

        # ==========================================
        # ABA 6: DIÁRIO DE BORDO
        # ==========================================
        dia_vitoria = ft.TextField(label="Maior Vitória do Dia", multiline=True, border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        dia_licao = ft.TextField(label="Lição Aprendida para a Vida", multiline=True, border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        dia_desabafo = ft.TextField(label="Espaço para Desabafo Livre", multiline=True, border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        lista_diario_ui = ft.Column(spacing=10)

        def carregar_diario():
            try:
                lista_diario_ui.controls.clear()
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT id, vitoria, licao, desabafo, data FROM diario ORDER BY id DESC")
                rows = c.fetchall()
                conn.close()

                for dia_id, vit, lic, des, dt in rows:
                    def deletar_diario(e, id_item=dia_id):
                        conn = sqlite3.connect(DB_PATH)
                        cur = conn.cursor()
                        cur.execute("DELETE FROM diario WHERE id = ?", (id_item,))
                        conn.commit()
                        conn.close()
                        carregar_diario()
                        carregar_resumo_dia()

                    lista_diario_ui.controls.append(
                        card_premium(
                            ft.Column([
                                ft.Row([
                                    ft.Text(f"Registro em: {dt or ''}", size=12, weight=ft.FontWeight.BOLD, color="#EC4899"),
                                    ft.IconButton(icon=ft.icons.DELETE, icon_color="#EF4444", tooltip="Apagar", on_click=deletar_diario)
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Text(f"🏆 Vitória: {vit}", size=11, color="#FFFFFF") if vit else ft.Container(),
                                ft.Text(f"💡 Lição: {lic}", size=11, color="#00F2FE") if lic else ft.Container(),
                                ft.Text(f"💬 Desabafo: {des}", size=11, color="#9CA3AF") if des else ft.Container()
                            ]), glow_color="#EC4899"
                        )
                    )
                page.update()
            except: pass

        def salvar_diario(e):
            if dia_vitoria.value or dia_licao.value or dia_desabafo.value:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO diario (vitoria, licao, desabafo, data) VALUES (?, ?, ?, ?)",
                          (dia_vitoria.value or "", dia_licao.value or "", dia_desabafo.value or "", data_formatada))
                conn.commit()
                conn.close()
                add_xp(20) 
                dia_vitoria.value = ""
                dia_licao.value = ""
                dia_desabafo.value = ""
                carregar_diario()
                carregar_resumo_dia()

        view_diario = ft.Container(
            content=ft.Column([
                cabecalho("6. Retrospectiva & Mindset", "Análise do seu estado mental e desabafo", "#EC4899"),
                dia_vitoria, dia_licao, dia_desabafo,
                ft.ElevatedButton("REGISTRAR DIÁRIO", bgcolor="#EC4899", color="#FFFFFF", height=45, on_click=salvar_diario),
                ft.Text("REFLEXÕES REGISTRADAS", size=12, weight=ft.FontWeight.BOLD, color="#9CA3AF"),
                lista_diario_ui
            ], spacing=12, scroll=ft.ScrollMode.AUTO),
            padding=15, expand=True
        )

        # ==========================================
        # ABA 7: WORKOUT & RASTREIO DE TREINOS
        # ==========================================
        txt_nome_treino = ft.TextField(label="Nome do Treino (Ex: Peito/Tríceps)", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        txt_lista_exercicios = ft.TextField(label="Exercícios (Separados por vírgula)", hint_text="Ex: Supino Reto, Supino Inclinado", multiline=True, border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        
        dd_treino_ativo = ft.Dropdown(label="Selecione o Treino", border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"))
        painel_overview_treino = ft.Column(spacing=8)
        painel_execucao_treino = ft.Column(spacing=10)
        
        hora_inicio_treino = [None]
        inputs_cargas = {}

        def atualizar_overview_treino(e):
            try:
                painel_overview_treino.controls.clear()
                painel_execucao_treino.controls.clear()
                if not dd_treino_ativo.value: 
                    page.update()
                    return

                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT nome_treino, exercicios FROM treinos_master WHERE id = ?", (int(dd_treino_ativo.value),))
                row = c.fetchone()
                conn.close()

                if row:
                    nome_t, ex_str = row
                    exercicios = [ex.strip() for ex in ex_str.split(",") if ex.strip()]
                    lista_ex_fmt = "\n".join([f"  • {ex}" for ex in exercicios])
                    
                    def deletar_treino_master_btn(ev):
                        try:
                            t_id = dd_treino_ativo.value
                            if t_id:
                                cn = sqlite3.connect(DB_PATH)
                                cur = cn.cursor()
                                cur.execute("DELETE FROM treinos_master WHERE id = ?", (int(t_id),))
                                cn.commit()
                                cn.close()
                                dd_treino_ativo.value = None
                                painel_overview_treino.controls.clear()
                                carregar_treinos_master()
                                page.update()
                        except: pass

                    painel_overview_treino.controls.append(
                        card_premium(
                            ft.Column([
                                ft.Row([
                                    ft.Text(f"📋 PRÉVIA DA FICHA: {nome_t.upper()}", size=12, weight=ft.FontWeight.BOLD, color="#FF0055"),
                                    ft.IconButton(icon=ft.icons.DELETE, icon_color="#EF4444", tooltip="Apagar Ficha Master", on_click=deletar_treino_master_btn)
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Text(f"Exercícios inclusos nesta sessão:\n{lista_ex_fmt}", size=11, color="#FFFFFF"),
                                ft.ElevatedButton("▶️ INICIAR TREINO AGORA", bgcolor="#10B981", color="#000000", height=45, on_click=iniciar_sessao_treino)
                            ]), glow_color="#FF0055"
                        )
                    )
                page.update()
            except Exception as ex:
                print(f"Erro em atualizar_overview_treino: {ex}")

        dd_treino_ativo.on_change = atualizar_overview_treino

        def carregar_treinos_master():
            try:
                dd_treino_ativo.options.clear()
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT id, nome_treino FROM treinos_master")
                rows = c.fetchall()
                for id_t, nm in rows:
                    dd_treino_ativo.options.append(ft.dropdown.Option(key=str(id_t), text=nm))
                conn.close()
                page.update()
            except Exception as ex:
                print(f"Erro em carregar_treinos_master: {ex}")

        def salvar_treino_master(e):
            if txt_nome_treino.value and txt_lista_exercicios.value:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO treinos_master (nome_treino, exercicios) VALUES (?, ?)", (txt_nome_treino.value, txt_lista_exercicios.value))
                conn.commit()
                conn.close()
                txt_nome_treino.value = ""
                txt_lista_exercicios.value = ""
                carregar_treinos_master()

        def iniciar_sessao_treino(e):
            try:
                if not dd_treino_ativo.value: return
                hora_inicio_treino[0] = datetime.now()
                painel_overview_treino.controls.clear()
                painel_execucao_treino.controls.clear()
                inputs_cargas.clear()

                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT nome_treino, exercicios FROM treinos_master WHERE id = ?", (int(dd_treino_ativo.value),))
                row = c.fetchone()
                conn.close()

                if row:
                    nome_t, ex_str = row
                    exercicios = [ex.strip() for ex in ex_str.split(",") if ex.strip()]
                    painel_execucao_treino.controls.append(ft.Text(f"⏱️ TREINO EM ANDAMENTO: {nome_t}", size=14, weight=ft.FontWeight.BOLD, color="#FF0055"))

                    for ex in exercicios:
                        tf_carga = ft.TextField(label=f"Carga {ex} (kg)", border_color="#1F293D", color="#FFFFFF", text_size=11)
                        chk = ft.Checkbox(label=f"Concluído: {ex}", fill_color="#FF0055")
                        inputs_cargas[ex] = (tf_carga, chk)
                        painel_execucao_treino.controls.append(
                            ft.Container(content=ft.Column([tf_carga, chk]), padding=10, bgcolor="#0B0E14", border_radius=8, border=ft.border.all(1, "#1F293D"))
                        )

                    def finalizar_treino(ev):
                        if not hora_inicio_treino[0]: return
                        duracao = int((datetime.now() - hora_inicio_treino[0]).total_seconds() / 60)
                        resumo_cargas = []
                        for ex_nome, (input_c, check_c) in inputs_cargas.items():
                            status = "✅" if check_c.value else "❌"
                            resumo_cargas.append(f"{status} {ex_nome}: {input_c.value or '0'}kg")

                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("INSERT INTO historico_treinos (nome_treino, duracao_min, detalhes_cargas, data) VALUES (?, ?, ?, ?)",
                                  (nome_t, f"{duracao} min", " | ".join(resumo_cargas), data_formatada))
                        conn.commit()
                        conn.close()
                        add_xp(50) 

                        painel_execucao_treino.controls.clear()
                        painel_execucao_treino.controls.append(ft.Text(f"🎉 TREINO DE {duracao} MINUTOS SALVO!", size=12, color="#10B981", weight=ft.FontWeight.BOLD))
                        carregar_historico_treinos()
                        carregar_resumo_dia()
                        page.update()

                    def cancelar_treino(ev):
                        hora_inicio_treino[0] = None
                        painel_execucao_treino.controls.clear()
                        atualizar_overview_treino(None)

                    painel_execucao_treino.controls.append(
                        ft.Column([
                            ft.ElevatedButton("🏁 FINALIZAR TREINO", bgcolor="#FF0055", color="#FFFFFF", height=45, on_click=finalizar_treino),
                            ft.ElevatedButton("❌ CANCELAR SESSÃO DE TREINO", bgcolor="#1F293D", color="#EF4444", height=40, on_click=cancelar_treino)
                        ], spacing=8)
                    )
                page.update()
            except Exception as ex:
                print(f"Erro em iniciar_sessao_treino: {ex}")

        lista_historico_treinos_ui = ft.Column(spacing=10)

        def carregar_historico_treinos():
            try:
                lista_historico_treinos_ui.controls.clear()
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT id, nome_treino, duracao_min, detalhes_cargas, data FROM historico_treinos ORDER BY id DESC")
                rows = c.fetchall()
                conn.close()

                for t_id, nm, dur, det, dt in rows:
                    def deletar_treino(e, id_item=t_id):
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("DELETE FROM historico_treinos WHERE id = ?", (id_item,))
                        conn.commit()
                        conn.close()
                        carregar_historico_treinos()
                        carregar_resumo_dia()

                    lista_historico_treinos_ui.controls.append(
                        card_premium(
                            ft.Column([
                                ft.Row([
                                    ft.Text(f"🏋️ {nm}", size=13, weight=ft.FontWeight.BOLD, color="#FF0055"),
                                    ft.Text(f"⏱️ {dur} • {dt}", size=10, color="#6B7280"),
                                    ft.IconButton(icon=ft.icons.DELETE, icon_color="#EF4444", tooltip="Apagar Histórico de Treino", on_click=deletar_treino)
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Text(det, size=11, color="#FFFFFF")
                            ]), glow_color="#FF0055"
                        )
                    )
                page.update()
            except Exception as ex:
                print(f"Erro em carregar_historico_treinos: {ex}")

        view_treino = ft.Container(
            content=ft.Column([
                cabecalho("7. Central de Treino & Performance", "Monte seus treinos master e registre suas sessões", "#FF0055"),
                card_premium(
                    ft.Column([
                        ft.Text("CRIAR FICHA MASTER DE TREINO", size=11, color="#FF0055", weight=ft.FontWeight.BOLD),
                        txt_nome_treino, txt_lista_exercicios,
                        ft.ElevatedButton("Salvar Treino Master", bgcolor="#FF0055", color="#FFFFFF", on_click=salvar_treino_master)
                    ], spacing=8), glow_color="#1F293D"
                ),
                ft.Divider(color="#1F293D", height=10),
                ft.Text("SELECIONAR TREINO", size=12, weight=ft.FontWeight.BOLD, color="#9CA3AF"),
                dd_treino_ativo, 
                painel_overview_treino, 
                painel_execucao_treino,
                ft.Divider(color="#1F293D", height=10),
                ft.Text("HISTÓRICO DE TREINOS EXECUTADOS", size=12, weight=ft.FontWeight.BOLD, color="#9CA3AF"),
                lista_historico_treinos_ui
            ], spacing=12, scroll=ft.ScrollMode.AUTO),
            padding=15, expand=True
        )

        # ==========================================
        # ABA 8: DASHBOARD & BI (VISÃO 360)
        # ==========================================
        input_data_pesquisa = ft.TextField(
            value=data_formatada, label="Data de Consulta (DD/MM/YYYY)",
            border_color="#1F293D", color="#FFFFFF", label_style=ft.TextStyle(color="#9CA3AF"), expand=True
        )

        conteudo_resumo = ft.Column(spacing=10)

        def carregar_resumo_dia(e=None):
            try:
                dt_busca = input_data_pesquisa.value.strip() or data_formatada
                conteudo_resumo.controls.clear()

                try:
                    partes = dt_busca.split("/")
                    iso_busca = f"{partes[2]}-{partes[1]}-{partes[0]}"
                except:
                    iso_busca = data_hoje_iso

                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()

                # 1. ROTINA & CONSISTÊNCIA + FALHAS CRUZADAS
                c.execute("SELECT rotina, tipo_excecao, motivo, horario_real FROM excecoes WHERE data = ?", (dt_busca,))
                excecoes_dict = {r[0]: (r[1], r[2], r[3]) for r in c.fetchall()}

                c.execute("SELECT id, atividade, horario FROM rotina_master WHERE dia_semana = ?", (dia_semana_hoje,))
                todas_rotinas = c.fetchall()
                total_rotinas = len(todas_rotinas)
                
                rot_ok, rot_atraso, rot_pend = [], [], []

                for rot_id, ativ, hor in todas_rotinas:
                    c.execute("SELECT cumprido FROM execucao_rotina WHERE rotina_id = ? AND data = ?", (rot_id, iso_busca))
                    res = c.fetchone()
                    foi_cumprido = bool(res[0]) if res else False
                    exc_reg = excecoes_dict.get(ativ)

                    if foi_cumprido:
                        if exc_reg and "Atraso" in str(exc_reg[0]):
                            rot_atraso.append(f"🟡 {ativ} (Prev: {hor} | Real: {exc_reg[2] or '?'})")
                        else:
                            rot_ok.append(f"🟢 {ativ} ({hor})")
                    else:
                        if exc_reg:
                            rot_pend.append(f"🔴 {ativ} ({hor}) ➔ {exc_reg[0]}: {exc_reg[1]}")
                        else:
                            rot_pend.append(f"🔴 {ativ} ({hor}) ➔ Não realizado")

                cump_count = len(rot_ok) + len(rot_atraso)
                pct_rot = int((cump_count / total_rotinas * 100)) if total_rotinas > 0 else 0

                conteudo_resumo.controls.append(
                    card_premium(
                        ft.Column([
                            ft.Row([ft.Text("📋 ROTINA & CONSISTÊNCIA", size=12, weight=ft.FontWeight.BOLD, color="#00F2FE"), ft.Text(f"{pct_rot}%", size=14, weight=ft.FontWeight.BOLD, color="#10B981" if pct_rot>=70 else "#EF4444")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Text("\n".join(rot_ok) if rot_ok else "", size=11, color="#10B981"),
                            ft.Text("\n".join(rot_atraso) if rot_atraso else "", size=11, color="#F59E0B"),
                            ft.Text("\n".join(rot_pend) if rot_pend else "", size=11, color="#EF4444"),
                        ]), glow_color="#00F2FE"
                    )
                )

                # 2. GAPS / TEMPO LIVRE
                c.execute("SELECT horario, atividade, impacto FROM gaps WHERE data = ?", (dt_busca,))
                gaps_dia = c.fetchall()
                if gaps_dia:
                    txt_gaps = "\n".join([f"⏱️ {hor}: {ativ} ({imp})" for hor, ativ, imp in gaps_dia])
                    conteudo_resumo.controls.append(
                        card_premium(
                            ft.Column([
                                ft.Text("⏳ TEMPO LIVRE & GAPS REGISTRADOS", size=12, weight=ft.FontWeight.BOLD, color="#F59E0B"),
                                ft.Text(txt_gaps, size=11, color="#FFFFFF")
                            ]), glow_color="#F59E0B"
                        )
                    )

                # 3. AUDITORIA DE FALHAS
                c.execute("SELECT rotina, tipo_excecao, motivo, solucao FROM excecoes WHERE data = ?", (dt_busca,))
                excecoes_lista = c.fetchall()
                if excecoes_lista:
                    txt_excecoes = "\n".join([f"⚠️ {rot} ({t_exc})\n   • Motivo: {mot}\n   • Plano de Ação: {sol or 'N/A'}" for rot, t_exc, mot, sol in excecoes_lista])
                    conteudo_resumo.controls.append(
                        card_premium(
                            ft.Column([
                                ft.Text("🚨 AUDITORIA DE FALHAS DO DIA", size=12, weight=ft.FontWeight.BOLD, color="#EF4444"),
                                ft.Text(txt_excecoes, size=11, color="#FFFFFF")
                            ]), glow_color="#EF4444"
                        )
                    )

                # 4. MOVIMENTAÇÃO FINANCEIRA
                c.execute("SELECT descricao, valor, categoria, tipo FROM financas WHERE data = ?", (dt_busca,))
                financas_dia = c.fetchall()
                gasto_dia = sum(val for _, val, _, t in financas_dia if t == 'saida')
                entrada_dia = sum(val for _, val, _, t in financas_dia if t == 'entrada')
                txt_compras = "\n".join([f"• {desc}: {'+' if t=='entrada' else '-'} R$ {val:,.2f} ({cat})" for desc, val, cat, t in financas_dia]) if financas_dia else "Nenhuma movimentação financeira hoje."
                
                conteudo_resumo.controls.append(
                    card_premium(
                        ft.Column([
                            ft.Row([ft.Text("💰 MOVIMENTAÇÃO FINANCEIRA", size=12, weight=ft.FontWeight.BOLD, color="#8B5CF6"), ft.Text(f"Gastos: R$ {gasto_dia:,.2f} | Entradas: R$ {entrada_dia:,.2f}", size=11, weight=ft.FontWeight.BOLD, color="#D1D5DB")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Text(txt_compras, size=11, color="#FFFFFF")
                        ]), glow_color="#8B5CF6"
                    )
                )

                # 5. TREINOS, DIETA & HIDRATAÇÃO
                c.execute("SELECT nome_treino, duracao_min, detalhes_cargas FROM historico_treinos WHERE data = ?", (dt_busca,))
                treinos_dia = c.fetchall()
                c.execute("SELECT tipo, descricao FROM refeicoes WHERE data = ?", (dt_busca,))
                refeicoes_dia = c.fetchall()
                c.execute("SELECT vitoria, desabafo FROM diario WHERE data = ?", (dt_busca,))
                diario_dia = c.fetchone()
                
                c.execute("SELECT copos FROM agua_diaria WHERE data = ?", (dt_busca,))
                res_agua_dia = c.fetchone()
                copos_dia_resumo = res_agua_dia[0] if res_agua_dia else 0
                litros_dia = copos_dia_resumo * 0.25
                
                txt_agua = f"💧 Água: {litros_dia:.2f}L / 3.0L (" + ("✅ Meta Atingida!" if litros_dia >= 3.0 else "🔴 Faltou água!") + ")"
                cor_agua = "#10B981" if litros_dia >= 3.0 else "#EF4444"

                conn.close()

                conteudo_resumo.controls.append(
                    card_premium(
                        ft.Column([
                            ft.Text("🏋️ TREINOS, DIETA & HIDRATAÇÃO", size=12, weight=ft.FontWeight.BOLD, color="#10B981"),
                            ft.Text(txt_agua, size=11, weight=ft.FontWeight.BOLD, color=cor_agua),
                            ft.Text("\n".join([f"🏋️ {n} ({d})\n   {c}" for n, d, c in treinos_dia]) if treinos_dia else "Sem treino.", size=11, color="#FFFFFF"),
                            ft.Text("\n".join([f"🥗 {t}: {d}" for t, d in refeicoes_dia]) if refeicoes_dia else "Sem refeições.", size=11, color="#D1D5DB")
                        ]), glow_color="#10B981"
                    )
                )

                if diario_dia:
                    conteudo_resumo.controls.append(
                        card_premium(
                            ft.Column([
                                ft.Text("🧠 MINDSET", size=12, weight=ft.FontWeight.BOLD, color="#EC4899"),
                                ft.Text(f"🏆 Vitória: {diario_dia[0] or 'N/A'}", size=11, color="#FFFFFF"),
                                ft.Text(f"💬 Desabafo: {diario_dia[1] or 'N/A'}", size=11, color="#9CA3AF")
                            ]), glow_color="#EC4899"
                        )
                    )

                page.update()
            except Exception as ex:
                print(f"Erro no resumo: {ex}")

        view_analytics = ft.Container(
            content=ft.Column([
                cabecalho("8. Visão 360 & Analytics", "Resumo detalhado com gráficos", "#3B82F6"),
                ft.Row([input_data_pesquisa, ft.ElevatedButton("Buscar 🔍", bgcolor="#3B82F6", color="#FFFFFF", height=48, on_click=carregar_resumo_dia)]),
                ft.Divider(color="#1F293D", height=10),
                conteudo_resumo
            ], spacing=12, scroll=ft.ScrollMode.AUTO),
            padding=15, expand=True
        )

        # ==========================================
        # NAVEGAÇÃO CENTRAL & MONTAGEM FINAL
        # ==========================================
        body = ft.Container(content=view_rotina, expand=True)

        def navegar(e):
            telas = [view_rotina, view_gaps, view_excecoes, view_nutricao, view_financas, view_diario, view_treino, view_analytics]
            body.content = telas[e.control.selected_index]
            page.update()

        navegacao = ft.NavigationBar(
            selected_index=0,
            bgcolor="#05070A",
            indicator_color="#00F2FE",
            on_change=navegar,
            destinations=[
                ft.NavigationDestination(icon=ft.icons.CHECK_BOX, label="Rotina"),
                ft.NavigationDestination(icon=ft.icons.TIMELAPSE, label="Gaps"),
                ft.NavigationDestination(icon=ft.icons.REPORT_PROBLEM, label="Falhas"),
                ft.NavigationDestination(icon=ft.icons.FITNESS_CENTER, label="Saúde"),
                ft.NavigationDestination(icon=ft.icons.ACCOUNT_BALANCE_WALLET, label="Cofre"),
                ft.NavigationDestination(icon=ft.icons.AUTO_STORIES, label="Diário"),
                ft.NavigationDestination(icon=ft.icons.SPORTS_GYMNASTICS, label="Treino"),
                ft.NavigationDestination(icon=ft.icons.PIE_CHART, label="Visão"),
            ]
        )

        page.add(
            ft.Column([
                painel_gamificacao, 
                body, 
                navegacao
            ], expand=True, spacing=0)
        )

        # Inicializações seguras no arranque
        try: atualizar_header_xp()
        except: pass
        
        try: carregar_rotina_do_dia()
        except: pass

        try: carregar_gaps()
        except: pass

        try: carregar_excecoes()
        except: pass

        try: carregar_refeicoes()
        except: pass

        try: atualizar_financeiro()
        except: pass

        try: carregar_diario()
        except: pass

        try: carregar_treinos_master()
        except: pass

        try: carregar_historico_treinos()
        except: pass

        try: carregar_resumo_dia()
        except: pass

    except Exception as e:
        erro_completo = traceback.format_exc()
        page.add(
            ft.Text("🚨 ERRO DETECTADO:", size=18, color="red", weight="bold"),
            ft.Container(
                content=ft.Text(erro_completo, color="white", size=10, selectable=True),
                bgcolor="#220000",
                padding=10,
                border_radius=5
            )
        )

if __name__ == "__main__":
    ft.app(target=main)
