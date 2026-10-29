 

""" 

Automação de aptidão para prova. 

 

Consolida inscritos, progresso em cursos, notas e presença em lives, 

calcula a aptidão de cada aluno e exporta o resultado. 

""" 

 

import io 

import os 

import re 

 

import pandas as pd 

from google.colab import auth, drive, files 

 

# ================================================================= 

# CONFIGURAÇÕES (ajuste antes de executar) 

# ================================================================= 

ID_PLANILHA_LOOKER = "SEU_ID_DA_PLANILHA_AQUI" 

CAMINHO_BASE = "/content/drive/My Drive/PASTA/BASE_ALUNOS.xlsx" 

ABA_SHEETS = "Base_Dashboard" 

 

cursos_alvo = [ 

    "Curso Exemplo | Dia 1", 

    "Curso Exemplo | Dia 2 (Rota + Missão)", 

    "Curso Exemplo | Dia 3", 

    "Curso Exemplo | Dia 4 (Rota + Missão)", 

    "Curso Exemplo | Dia 5", 

    "Curso Exemplo | Dia 8", 

    "Curso Exemplo | Dia 9 (Rota + Missão)", 

    "Curso Exemplo | Dia 10", 

    "Curso Exemplo | Dia 11", 

    "Compromisso Final", 

] 

 

lives_alvo = [ 

    "[LIVE] Boas Vindas", 

    "[LIVE] História da Empresa", 

    "[LIVE] Nosso Negócio", 

    "[LIVE] Processo de Vendas", 

    "[LIVE] Diagnóstico - Vender", 

    "[LIVE] Diagnóstico - Gerir", 

    "[LIVE] Diagnóstico - Girar", 

    "[LIVE] Negociação e Objeções", 

    "[LIVE] Precificação", 

    "[LIVE] Planejamento", 

    "[LIVE] Encantamento do Cliente", 

] 

 

PESOS_STATUS = {"Concluído": 3, "Incompleto": 2, "Não Iniciado": 1, "Faltou": 1} 

MINIMO_PRESENCA = 0.90 

 

 

# ================================================================= 

# FUNÇÕES AUXILIARES 

# ================================================================= 

def chave(texto): 

    """Normaliza um texto para comparação: maiúsculas e apenas letras e números. 

 

    Evita falsos positivos por substring, como 'DIA1' contido em 'DIA10'. 

    """ 

    return re.sub(r"[^A-Z0-9]", "", str(texto).upper()) 

 

 

def ler_arquivo(nome, conteudo): 

    """Lê Excel ou CSV, tentando UTF-8 e depois Latin-1.""" 

    if nome.endswith((".xlsx", ".xls")): 

        return pd.read_excel(io.BytesIO(conteudo)) 

    try: 

        return pd.read_csv(io.BytesIO(conteudo), sep=None, engine="python", encoding="utf-8") 

    except UnicodeDecodeError: 

        return pd.read_csv(io.BytesIO(conteudo), sep=None, engine="python", encoding="latin1") 

 

 

def definir_status_curso(valor_status, valor_progresso): 

    """Converte status e progresso da plataforma em Concluído, Incompleto ou Não Iniciado.""" 

    status = str(valor_status).strip().lower() 

    progresso = str(valor_progresso).strip().lower().replace(" ", "") 

 

    if any(t in status for t in ["completo", "concluído", "concluido", "aprovado", "finalizado"]): 

        return "Concluído" 

    if "100%" in progresso: 

        return "Concluído" 

 

    match = re.search(r"(\d+)\s*(?:de|/)\s*(\d+)", progresso) 

    if match: 

        feitos, total = int(match.group(1)), int(match.group(2)) 

        if total > 0 and feitos >= total: 

            return "Concluído" 

        if feitos > 1: 

            return "Incompleto" 

 

    return "Não Iniciado" 

 

 

def verificar_aptidao(df): 

    """Marca SIM se o aluno concluiu todos os cursos e teve presença mínima nas lives.""" 

 

    def avaliar(row): 

        if any(str(row.get(c, "")) != "Concluído" for c in cursos_alvo): 

            return "NÃO" 

        presencas = sum(1 for live in lives_alvo if row.get(live) == "Presente") 

        return "SIM" if presencas / len(lives_alvo) >= MINIMO_PRESENCA else "NÃO" 

 

    df["APTO PARA REALIZAR A PROVA"] = df.apply(avaliar, axis=1) 

    return df 

 

 

def localizar_coluna(df, termos, padrao): 

    """Retorna a primeira coluna cujo nome contém algum dos termos.""" 

    for col in df.columns: 

        if any(t in col for t in termos): 

            return col 

    return padrao 

 

 

# ================================================================= 

# AUTENTICAÇÃO 

# ================================================================= 

auth.authenticate_user() 

drive.mount("/content/drive", force_remount=True) 

 

import gspread 

from google.auth import default 

 

creds, _ = default() 

gc = gspread.authorize(creds) 

 

 

# ================================================================= 

# CARREGAR BASE OU CRIAR NOVA 

# ================================================================= 

if os.path.exists(CAMINHO_BASE): 

    df_base = pd.read_excel(CAMINHO_BASE) 

    colunas_identidade = ["ETIQUETA", "FUNÇÃO", "EMAIL DO FRANQUEADO"] 

    for col in colunas_identidade + cursos_alvo + lives_alvo + ["Nota Teste Final"]: 

        if col not in df_base.columns: 

            if "Nota" in col: 

                df_base[col] = 0 

            elif col in lives_alvo: 

                df_base[col] = "Faltou" 

            elif col in colunas_identidade: 

                df_base[col] = "" 

            else: 

                df_base[col] = "Não Iniciado" 

    print("Base carregada.") 

    escolha = input("[U] Atualizar | [A] Adicionar/Mesclar | [C] Novo mês: ").strip().upper() 

else: 

    escolha = "C" 

 

if escolha in ["C", "A"]: 

    print("Envie o arquivo de inscritos:") 

    upload = files.upload() 

    nome_arquivo = list(upload.keys())[0] 

    df_n = ler_arquivo(nome_arquivo, upload[nome_arquivo]) 

    df_n.columns = [str(c).upper().strip() for c in df_n.columns] 

 

    df_n = df_n.rename(columns={ 

        localizar_coluna(df_n, ["NOME", "USUÁRIO"], "NOME"): "NOME", 

        localizar_coluna(df_n, ["FRANQUIA", "POLO"], "FRANQUIA"): "FRANQUIA", 

        localizar_coluna(df_n, ["EMAIL", "LOGIN", "E-MAIL"], "EMAIL"): "EMAIL", 

        localizar_coluna(df_n, ["ETIQUETA"], "ETIQUETA"): "ETIQUETA", 

        localizar_coluna(df_n, ["FUNÇÃO", "FUNCAO", "ROLE"], "FUNÇÃO"): "FUNÇÃO", 

        localizar_coluna(df_n, ["EMAIL DO FRANQUEADO", "EMAIL FRANQUEADO"], "EMAIL DO FRANQUEADO"): "EMAIL DO FRANQUEADO", 

    }) 

 

    cols_finais = ["NOME", "FRANQUIA", "EMAIL", "ETIQUETA", "FUNÇÃO", "EMAIL DO FRANQUEADO"] 

    for col in cols_finais: 

        if col not in df_n.columns: 

            df_n[col] = "" 

 

    df_n = df_n[cols_finais].drop_duplicates(subset=["EMAIL"]).copy() 

    df_n["EMAIL"] = df_n["EMAIL"].str.lower().str.strip() 

 

    if escolha == "C": 

        df_base = df_n.copy() 

        for c in cursos_alvo: 

            df_base[c] = "Não Iniciado" 

        for live in lives_alvo: 

            df_base[live] = "Faltou" 

        df_base["Nota Teste Final"] = 0 

    else: 

        df_base["EMAIL"] = df_base["EMAIL"].str.lower().str.strip() 

        for _, row in df_n.iterrows(): 

            existe = df_base["EMAIL"].values == row["EMAIL"] 

            if existe.any(): 

                idx = df_base[existe].index[0] 

                for col in ["ETIQUETA", "FUNÇÃO", "EMAIL DO FRANQUEADO", "FRANQUIA", "NOME"]: 

                    if str(df_base.at[idx, col]).strip().lower() in ["", "nan", "none"]: 

                        df_base.at[idx, col] = row[col] 

            else: 

                novo = pd.DataFrame([row]) 

                for c in cursos_alvo: 

                    novo[c] = "Não Iniciado" 

                for live in lives_alvo: 

                    novo[live] = "Faltou" 

                novo["Nota Teste Final"] = 0 

                df_base = pd.concat([df_base, novo], ignore_index=True) 

 

 

# ================================================================= 

# ATUALIZAÇÕES (cursos, notas e lives) 

# ================================================================= 

count_updates = 0 

 

# 1. Cursos 

if input("\nAtualizar cursos? (s/n): ").strip().lower() == "s": 

    uploads_cursos = files.upload() 

    for nome, conteudo in uploads_cursos.items(): 

        df_u = ler_arquivo(nome, conteudo) 

        df_u.columns = [str(c).strip() for c in df_u.columns] 

 

        c_login = localizar_coluna(df_u, ["LOGIN", "EMAIL", "E-MAIL"], "Login") 

        c_curso = next( 

            (c for c in df_u.columns if "nome do curso" in c.lower() or c.lower() == "curso" or "trilha" in c.lower()), 

            "Nome do curso", 

        ) 

        c_status = localizar_coluna(df_u, ["STATUS"], "Status") 

        c_prog = localizar_coluna(df_u, ["PROGRESSO"], "Progresso") 

 

        df_u["_login"] = df_u[c_login].astype(str).str.lower().str.strip() 

        df_u["_curso"] = df_u[c_curso].apply(chave) 

 

        for idx, row in df_base.iterrows(): 

            email = str(row["EMAIL"]).lower().strip() 

            registros = df_u[df_u["_login"] == email] 

            if registros.empty: 

                continue 

 

            for curso in cursos_alvo: 

                if curso == "Compromisso Final": 

                    mask = registros["_curso"].str.contains(chave(curso), regex=False) 

                else: 

                    mask = registros["_curso"] == chave(curso) 

 

                regs_curso = registros[mask] 

                if regs_curso.empty: 

                    continue 

 

                status_novo = max( 

                    (definir_status_curso(r.get(c_status, ""), r.get(c_prog, "")) for _, r in regs_curso.iterrows()), 

                    key=lambda s: PESOS_STATUS.get(s, 0), 

                ) 

                status_atual = str(df_base.at[idx, curso]).strip() 

                if PESOS_STATUS.get(status_novo, 0) >= PESOS_STATUS.get(status_atual, 0) and status_novo != status_atual: 

                    df_base.at[idx, curso] = status_novo 

                    count_updates += 1 

 

# 2. Notas do teste final 

if input("\nAtualizar notas do teste final? (s/n): ").strip().lower() == "s": 

    uploads_notas = files.upload() 

    for nome, conteudo in uploads_notas.items(): 

        df_nota = ler_arquivo(nome, conteudo) 

        df_nota.columns = [str(c).strip() for c in df_nota.columns] 

 

        c_nota_email = localizar_coluna(df_nota, ["EMAIL", "LOGIN"], "Login") 

        c_nota_val = localizar_coluna(df_nota, ["ATINGIDA"], "Nota atingida") 

 

        notas = pd.to_numeric( 

            df_nota[c_nota_val].astype(str).str.replace(",", ".").str.replace("%", ""), 

            errors="coerce", 

        ) 

        df_nota["_email"] = df_nota[c_nota_email].astype(str).str.lower().str.strip() 

        maior_por_email = notas.groupby(df_nota["_email"]).max() 

 

        for idx, row in df_base.iterrows(): 

            email = str(row["EMAIL"]).lower().strip() 

            if email in maior_por_email.index and pd.notna(maior_por_email[email]): 

                nota = maior_por_email[email] 

                if nota > float(df_base.at[idx, "Nota Teste Final"]): 

                    df_base.at[idx, "Nota Teste Final"] = nota 

                    count_updates += 1 

 

# 3. Lives 

if input("\nAtualizar lives? (s/n): ").strip().lower() == "s": 

    uploads_lives = files.upload() 

    for nome, conteudo in uploads_lives.items(): 

        for i, nome_live in enumerate(lives_alvo): 

            print(f"[{i}] {nome_live}") 

 

        escolha_live = None 

        while escolha_live is None: 

            entrada = input(f"Qual live é '{nome}'? (número): ").strip() 

            if entrada.isdigit() and int(entrada) < len(lives_alvo): 

                escolha_live = lives_alvo[int(entrada)] 

            else: 

                print("Número inválido, tente novamente.") 

 

        df_l = ler_arquivo(nome, conteudo) 

        df_l.columns = [str(c).strip() for c in df_l.columns] 

        c_email_live = next( 

            (c for c in df_l.columns if "email" in c.lower().replace("-", "") or "login" in c.lower()), 

            None, 

        ) 

        if c_email_live is None: 

            print(f"Coluna de e-mail não encontrada em '{nome}'. Arquivo ignorado.") 

            continue 

 

        emails_presentes = set(df_l[c_email_live].dropna().astype(str).str.lower().str.strip()) 

        antes = (df_base[escolha_live] == "Presente").sum() 

        df_base.loc[df_base["EMAIL"].str.lower().isin(emails_presentes), escolha_live] = "Presente" 

        count_updates += (df_base[escolha_live] == "Presente").sum() - antes 

 

 

# ================================================================= 

# FINALIZAÇÃO 

# ================================================================= 

df_base = verificar_aptidao(df_base) 

 

# Backup antes de sobrescrever 

if os.path.exists(CAMINHO_BASE): 

    df_base_antigo = pd.read_excel(CAMINHO_BASE) 

    df_base_antigo.to_excel(CAMINHO_BASE.replace(".xlsx", "_backup.xlsx"), index=False) 

 

df_base.to_excel(CAMINHO_BASE, index=False) 

 

# Monta os dados antes de limpar a aba, para não deixar a planilha vazia em caso de erro 

dados = [df_base.fillna("").astype(str).columns.tolist()] + df_base.fillna("").astype(str).values.tolist() 

sh = gc.open_by_key(ID_PLANILHA_LOOKER) 

ws = sh.worksheet(ABA_SHEETS) 

ws.clear() 

ws.update(dados) 

 

print(f"Base atualizada com sucesso. Total de alterações: {count_updates}") 