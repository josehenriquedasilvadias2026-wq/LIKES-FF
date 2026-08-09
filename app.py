from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json
import time
from datetime import datetime, timedelta, timezone
from Utilities.until import load_accounts
from Api.Account import get_garena_token, get_major_login
from Api.InGame import get_player_personal_show, get_player_stats, search_account_by_keyword

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
            'nivel': clan.get('clanlevel'),
            'membros': clan.get('membernum')
        },
        'pet': {
            'nivel': pet.get('level'),
            'selecionado': pet.get('isselected'),
            'nome': pet.get('name')
        },
        'passe': {
            'nivel': current_pass.get('maxlevel', 0),
            'status': 'comprado' if current_pass.get('ownedpass', False) else 'não comprado'
        }
    }

@app.route('/')
def index():
    """Renderiza a página principal com as bases de Info, Likes e Bio."""
    return render_template('index.html')

@app.route('/api/infor', methods=['GET'])
def api_infor():
    """Consulta informações públicas de um jogador usando apenas region e uid."""
    try:
        region = request.args.get('region', '').upper().strip()
        uid = request.args.get('uid', '').strip()
        if not region or not uid:
            return jsonify({'success': False, 'error': 'Missing parameters'}), 400
        if region not in accounts:
            return jsonify({'success': False, 'error': 'Invalid region'}), 400
        
        credentials = accounts[region]
        garena_token = get_garena_token(credentials['uid'], credentials['password'])
        if not garena_token or 'access_token' not in garena_token:
            return jsonify({'success': False, 'error': 'Garena auth failed'}), 401
            
        major_login = get_major_login(garena_token['access_token'], garena_token['open_id'])
        if not major_login or 'serverUrl' not in major_login:
            return jsonify({'success': False, 'error': 'Major login failed'}), 502
            
        player_info = get_player_personal_show(major_login['serverUrl'], major_login['token'], int(uid), False, 7, False, False)
        if not player_info:
            return jsonify({'success': False, 'error': 'Player not found'}), 404
            
        return jsonify(normalize_player_info(player_info, uid, region)), 200
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500

@app.route('/api/info', methods=['GET'])
def api_info():
    return api_infor()

@app.route('/api/likes', methods=['GET'])
def api_likes():
    try:
        region = request.args.get('region', '').upper().strip()
        uid = request.args.get('uid', '').strip()
        if not region or not uid:
            return jsonify({'success': False, 'error': 'Missing parameters'}), 400
        if region not in accounts:
            return jsonify({'success': False, 'error': 'Invalid region'}), 400
            
        creds = accounts[region]
        gtoken = get_garena_token(creds['uid'], creds['password'])
        mlogin = get_major_login(gtoken['access_token'], gtoken['open_id'])
        pinfo = get_player_personal_show(mlogin['serverUrl'], mlogin['token'], int(uid), False, 7, False, False)
        if not pinfo:
            return jsonify({'success': False, 'error': 'Player not found'}), 404
            
        norm = normalize_player_info(pinfo, uid, region)
        return jsonify({
            'success': True,
            'uid': norm['uid'],
            'nome': norm['nome'],
            'likes': norm['likes'],
            'regiao': norm['regiao']
        }), 200
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500

@app.route('/api/bio', methods=['GET'])
def api_bio():
    try:
        region = request.args.get('region', 'BR').upper().strip()
        uid = request.args.get('uid', '').strip()
        if not uid:
            return jsonify({'success': False, 'error': 'Missing uid'}), 400
        if region not in accounts:
            return jsonify({'success': False, 'error': 'Invalid region'}), 400
            
        creds = accounts[region]
        gtoken = get_garena_token(creds['uid'], creds['password'])
        mlogin = get_major_login(gtoken['access_token'], gtoken['open_id'])
        pinfo = get_player_personal_show(mlogin['serverUrl'], mlogin['token'], int(uid), False, 7, False, False)
        if not pinfo:
            return jsonify({'success': False, 'error': 'Player not found'}), 404
            
        norm = normalize_player_info(pinfo, uid, region)
        return jsonify({
            'success': True,
            'uid': norm['uid'],
            'nome': norm['nome'],
            'bio': norm['bio'],
            'regiao': norm['regiao']
        }), 200
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
