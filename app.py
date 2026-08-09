from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json
import time
from datetime import datetime, timedelta, timezone
from until import load_accounts
from Account import get_garena_token, get_major_login
from InGame import get_player_personal_show, get_player_stats, search_account_by_keyword


accounts = load_accounts()


app = Flask(__name__)
CORS(app)


def format_timestamp(ts):
    if not ts: return "N/A"
    try:
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return dt.strftime('%d/%m/%Y %H:%M:%S')
    except: return "N/A"


def rank_name(rank_code, points):
    # Lógica simplificada de nomes de patente (pode ser expandida)
    if rank_code >= 60: return "Desafiante"
    if rank_code >= 50: return "Mestre"
    if rank_code >= 40: return "Elite"
    if rank_code >= 30: return "Diamante"
    if rank_code >= 20: return "Platina"
    if rank_code >= 10: return "Ouro"
    return "Bronze/Prata"


def normalize_player_info(player_info, requested_uid, region):
    basic = player_info.get('basicinfo') or player_info.get('basicInfo') or {}
    social = player_info.get('socialinfo') or player_info.get('socialInfo') or {}
    clan = player_info.get('clanbasicinfo') or player_info.get('clanBasicInfo') or {}
    pet = player_info.get('petinfo') or player_info.get('petInfo') or {}
    pass_history = player_info.get('historyepinfo') or player_info.get('historyEpInfo') or []
    if isinstance(pass_history, dict):
        pass_history = [pass_history]
    current_pass = pass_history[-1] if pass_history else {}
    
    br_code = basic.get('rank', 0)
    br_points = basic.get('rankingpoints', 0)
    cs_code = basic.get('csrank', 0)
    cs_points = basic.get('csrankingpoints', 0)
    
    return {
        'nome': basic.get('nickname'),
        'uid': str(basic.get('accountid') or requested_uid),
        'bio': social.get('signature'),
        'likes': basic.get('liked', 0),
        'nivel': basic.get('level', 0),
        'experiencia': basic.get('exp', 0),
        'regiao': basic.get('region') or region,
        'data_criacao': format_timestamp(basic.get('createat')),
        'ultimo_login': format_timestamp(basic.get('lastloginat')),
        'rank': {
            'br': br_code,
            'br_pontos': br_points,
            'br_patente': rank_name(br_code, br_points),
            'cs': cs_code,
            'cs_pontos': cs_points,
            'cs_patente': rank_name(cs_code, cs_points),
            'br_maximo': basic.get('maxrank', 0),
            'cs_maximo': basic.get('csmaxrank', 0)
        },
        'clan': {
            'id': clan.get('clanid') or basic.get('clanid'),
            'nome': clan.get('clanname') or basic.get('clanname'),
