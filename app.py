from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import time
from datetime import datetime, timedelta, timezone
from Utilities.until import load_accounts
from Api.Account import get_garena_token, get_major_login
from Api.InGame import get_player_personal_show, get_player_stats, search_account_by_keyword


accounts = load_accounts()


app = Flask(__name__)
# Enable CORS for all origins on all routes
CORS(app)




@app.route('/get_search_account_by_keyword', methods=['GET'])
def get_search_account_by_keyword():
    try:
        # Get request parameters
        region = request.args.get('server', 'IND').upper()
        search_term = request.args.get('keyword')
        
        # Validate keyword parameter
        if not search_term:
            return json.dumps({"error": "Keyword parameter is required"}, indent=2), 400, {'Content-Type': 'application/json; charset=utf-8'}
        
        # Enforce minimum keyword length
        if len(search_term.strip()) < 3:
            return json.dumps({"error": "Keyword must be at least 3 characters long"}, indent=2), 400, {'Content-Type': 'application/json; charset=utf-8'}
        
        # Validate server exists in accounts
        if region not in accounts:
            return json.dumps({"error": f"Invalid server: {region}"}, indent=2), 400, {'Content-Type': 'application/json; charset=utf-8'}
        
        # Authenticate with Garena
        auth_response = get_garena_token(accounts[region]['uid'], accounts[region]['password'])
        if not auth_response or 'access_token' not in auth_response:
            return json.dumps({"error": "Authentication failed"}, indent=2), 401, {'Content-Type': 'application/json; charset=utf-8'}
        
        # Get major login credentials
        login_response = get_major_login(auth_response["access_token"], auth_response["open_id"])
        if not login_response or 'token' not in login_response:
            return json.dumps({"error": "Major login failed"}, indent=2), 401, {'Content-Type': 'application/json; charset=utf-8'}
        
        # Search for accounts
        search_results = search_account_by_keyword(login_response["serverUrl"], login_response["token"], search_term)
        
        # Return formatted response
        formatted_response = json.dumps(search_results, indent=2, ensure_ascii=False)
        return formatted_response, 200, {'Content-Type': 'application/json; charset=utf-8'}
        
    except KeyError as e:
        return json.dumps({"error": f"Missing configuration: {str(e)}"}, indent=2), 500, {'Content-Type': 'application/json; charset=utf-8'}
    except Exception as e:
        return json.dumps({"error": f"Internal server error: {str(e)}"}, indent=2), 500, {'Content-Type': 'application/json; charset=utf-8'}

@app.route('/get_player_stats', methods=['GET'])
def get_player_stat():
    try:
        # Get and validate parameters
        server = request.args.get('server', 'IND').upper()
        uid = request.args.get('uid')
        gamemode = request.args.get('gamemode', 'br').lower()
        matchmode = request.args.get('matchmode', 'CAREER').upper()

        # Validate required parameters
        if not uid:
            return jsonify({
                "success": False,
                "error": "Missing required parameter",
                "message": "UID parameter is required"
            }), 400

        if not uid.isdigit():
            return jsonify({
                "success": False,
                "error": "Invalid UID",
                "message": "UID must be a numeric value"
            }), 400

        # Validate server
        if server not in accounts:
            return jsonify({
                "success": False,
                "error": "Invalid server",
                "message": f"Server '{server}' not found. Available servers: {list(accounts.keys())}"
            }), 400

        # Validate gamemode
        if gamemode not in ['br', 'cs']:
            return jsonify({
                "success": False,
                "error": "Invalid gamemode",
                "message": "Gamemode must be 'br' or 'cs'"
            }), 400

        # Validate matchmode
        if matchmode not in ['CAREER', 'NORMAL', 'RANKED']:
            return jsonify({
                "success": False,
                "error": "Invalid matchmode",
                "message": "Matchmode must be 'CAREER', 'NORMAL', or 'RANKED'"
            }), 400

        # Step 1: Get Garena token
        try:
            garena_token_result = get_garena_token(accounts[server]['uid'], accounts[server]['password'])
            
            if not garena_token_result or 'access_token' not in garena_token_result:
                return jsonify({
                    "success": False,
                    "error": "Garena authentication failed",
                    "message": "Failed to obtain Garena access token"
                }), 401
                
        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Garena authentication error",
                "message": f"Failed to authenticate with Garena: {str(e)}"
            }), 502

        # Step 2: Get Major login
        try:
            major_login_result = get_major_login(garena_token_result["access_token"], garena_token_result["open_id"])
            
            if not major_login_result or 'token' not in major_login_result:
                return jsonify({
                    "success": False,
                    "error": "Major login failed",
                    "message": "Failed to obtain Major login token"
                }), 401
                
        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Major login error",
                "message": f"Failed to login to Major: {str(e)}"
            }), 502

        # Step 3: Get player stats
        try:
            player_stats = get_player_stats(
                major_login_result["token"], 
                major_login_result["serverUrl"], 
                gamemode, 
                uid, 
                matchmode
            )
            
            if not player_stats:
                return jsonify({
                    "success": False,
                    "error": "No stats data",
                    "message": "No player statistics found for the given parameters"
                }), 404

            # Return formatted JSON response
            return jsonify({
                "success": True,
                "data": player_stats,
                "metadata": {
                    "server": server,
                    "uid": uid,
                    "gamemode": gamemode,
                    "matchmode": matchmode
                }
            }), 200
            
        except ValueError as e:
            return jsonify({
                "success": False,
                "error": "Invalid request parameters",
                "message": str(e)
            }), 400
        except ConnectionError as e:
            return jsonify({
                "success": False,
                "error": "Connection error",
                "message": str(e)
            }), 503
        except ProtobufError as e:
            return jsonify({
                "success": False,
                "error": "Data processing error",
                "message": str(e)
            }), 500
        except APIError as e:
            return jsonify({
                "success": False,
                "error": "External API error",
                "message": str(e)
            }), 502
        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Stats retrieval error",
                "message": f"Failed to retrieve player stats: {str(e)}"
            }), 500

    except Exception as e:
        # Catch any unexpected errors
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": "An unexpected error occurred while processing your request"
        }), 500

@app.route('/get_player_personal_show', methods=['GET'])
def get_account_info():
    try:
        # Get parameters with defaults
        server = request.args.get('server', 'IND').upper()
        uid = request.args.get('uid')
        need_gallery_info = request.args.get('need_gallery_info', False)
        need_blacklist = request.args.get('need_blacklist', False)
        need_spark_info = request.args.get('need_spark_info', False)
        call_sign_src = request.args.get('call_sign_src', 7)
        
        # Validate UID parameter - must be integer
        if not uid:
            response = {
                "status": "error",
                "error": "Missing UID",
                "message": "Empty 'uid' parameter. Please provide a valid 'uid'.",
                "code": "MISSING_UID"
            }
            return jsonify(response), 400, {'Content-Type': 'application/json; charset=utf-8'}
        
        # Check if UID is a valid integer
        try:
            uid_int = int(uid)
            # Additional validation for UID range if needed
            if uid_int <= 0:
                response = {
                    "status": "error",
                    "error": "Invalid UID",
                    "message": "UID must be a positive integer.",
                    "code": "INVALID_UID_RANGE"
                }
                return jsonify(response), 400, {'Content-Type': 'application/json; charset=utf-8'}
        except (ValueError, TypeError):
            response = {
                "status": "error",
                "error": "Invalid UID",
                "message": "UID must be a valid integer.",
                "code": "INVALID_UID_FORMAT"
            }
            return jsonify(response), 400, {'Content-Type': 'application/json; charset=utf-8'}
        
        # Validate server parameter
        if server not in accounts:
            response = {
                "status": "error",
                "error": "Invalid Server",
                "message": f"Server '{server}' not found. Available servers: {list(accounts.keys())}",
                "available_servers": list(accounts.keys()),
                "code": "SERVER_NOT_FOUND"
            }
            return jsonify(response), 400, {'Content-Type': 'application/json; charset=utf-8'}
        
        # Validate need_gallery_info parameter
        try:
            if isinstance(need_gallery_info, str):
                if need_gallery_info.lower() in ['true', '1', 'yes']:
                    need_gallery_info = True
                elif need_gallery_info.lower() in ['false', '0', 'no']:
                    need_gallery_info = False
                else:
                    raise ValueError("Invalid boolean value")
            need_gallery_info = bool(need_gallery_info)
        except (ValueError, TypeError):
            response = {
                "status": "error",
                "error": "Invalid Parameter",
                "message": "need_gallery_info must be a boolean value (true/false, 1/0).",
                "code": "INVALID_GALLERY_PARAM"
            }
            return jsonify(response), 400, {'Content-Type': 'application/json; charset=utf-8'}
        
        
        # Validate need_blacklist parameter
        try:
            if isinstance(need_blacklist, str):
                if need_blacklist.lower() in ['true', '1', 'yes']:
                    need_blacklist = True
                elif need_blacklist.lower() in ['false', '0', 'no']:
                    need_blacklist = False
                else:
                    raise ValueError("Invalid boolean value")
            need_blacklist = bool(need_blacklist)
        except (ValueError, TypeError):
            response = {
                "status": "error",
                "error": "Invalid Parameter",
                "message": "need_blacklist must be a boolean value (true/false, 1/0).",
                "code": "INVALID_GALLERY_PARAM"
            }
            return jsonify(response), 400, {'Content-Type': 'application/json; charset=utf-8'}
        
        
        # Validate need_spark_info parameter
        try:
            if isinstance(need_spark_info, str):
                if need_spark_info.lower() in ['true', '1', 'yes']:
                    need_spark_info = True
                elif need_spark_info.lower() in ['false', '0', 'no']:
                    need_spark_info = False
                else:
                    raise ValueError("Invalid boolean value")
            need_spark_info = bool(need_spark_info)
        except (ValueError, TypeError):
            response = {
                "status": "error",
                "error": "Invalid Parameter",
                "message": "need_spark_info must be a boolean value (true/false, 1/0).",
                "code": "INVALID_GALLERY_PARAM"
            }
            return jsonify(response), 400, {'Content-Type': 'application/json; charset=utf-8'}
        
        
        
        
        
        # Validate call_sign_src parameter
        try:
            call_sign_src_int = int(call_sign_src)
            if call_sign_src_int < 0:
                response = {
                    "status": "error",
                    "error": "Invalid Parameter",
                    "message": "call_sign_src must be a non-negative integer.",
                    "code": "INVALID_CALL_SIGN_SRC"
                }
                return jsonify(response), 400, {'Content-Type': 'application/json; charset=utf-8'}
        except (ValueError, TypeError):
            response = {
                "status": "error",
                "error": "Invalid Parameter",
                "message": "call_sign_src must be a valid integer.",
                "code": "INVALID_CALL_SIGN_FORMAT"
            }
            return jsonify(response), 400, {'Content-Type': 'application/json; charset=utf-8'}
        
        # Check if server account credentials exist
        if 'uid' not in accounts[server] or 'password' not in accounts[server]:
            response = {
                "status": "error",
                "error": "Server Configuration Error",
                "message": f"Server '{server}' is missing required credentials.",
                "code": "SERVER_CONFIG_ERROR"
            }
            return jsonify(response), 500, {'Content-Type': 'application/json; charset=utf-8'}
        
        # Step 1: Get Garena token
        garena_token_result = get_garena_token(accounts[server]['uid'], accounts[server]['password'])
        if not garena_token_result or 'access_token' not in garena_token_result or 'open_id' not in garena_token_result:
            response = {
                "status": "error",
                "error": "Authentication Failed",
                "message": "Failed to obtain Garena token. Invalid credentials or service unavailable.",
                "code": "GARENA_AUTH_FAILED"
            }
            return jsonify(response), 401, {'Content-Type': 'application/json; charset=utf-8'}
        
        # Step 2: Get major login
        major_login_result = get_major_login(garena_token_result["access_token"], garena_token_result["open_id"])
        if not major_login_result or 'serverUrl' not in major_login_result or 'token' not in major_login_result:
            response = {
                "status": "error",
                "error": "Login Failed",
                "message": "Failed to perform major login. Service unavailable.",
                "code": "MAJOR_LOGIN_FAILED"
            }
            return jsonify(response), 401, {'Content-Type': 'application/json; charset=utf-8'}
        
        # Step 3: Get player personal show data
        player_personal_show_result = get_player_personal_show(
            major_login_result["serverUrl"], 
            major_login_result["token"], 
            uid_int, 
            need_gallery_info, 
            call_sign_src_int,
            need_blacklist, 
            need_spark_info
        )
        
        
        
        if not player_personal_show_result:
            response = {
                "status": "error",
                "error": "Data Not Found",
                "message": f"No player data found for UID: {uid_int}",
                "code": "PLAYER_DATA_NOT_FOUND"
            }
            return jsonify(response), 404, {'Content-Type': 'application/json; charset=utf-8'}
        
        # Success response
        formatted_json = json.dumps(player_personal_show_result, indent=2, ensure_ascii=False)
        return formatted_json, 200, {'Content-Type': 'application/json; charset=utf-8'}
    
    except Exception as e:
        # Log the unexpected error for debugging
        print(f"Unexpected error in get_player_personal_show: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        response = {
            "status": "error",
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing your request.",
            "code": "INTERNAL_SERVER_ERROR"
        }
        return jsonify(response), 500, {'Content-Type': 'application/json; charset=utf-8'}





def format_timestamp(value):
    """Converte epoch Unix em data e horário no fuso de Brasília (UTC-3)."""
    if value in (None, '', 0, '0'):
        return None
    try:
        timestamp = int(value)
        local_time = datetime.fromtimestamp(
            timestamp,
            tz=timezone(timedelta(hours=-3))
        )
        return local_time.strftime('%d/%m/%Y %H:%M:%S')
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def rank_name(rank_code, points=None):
    """Converte o código interno de rank em uma patente sem usar pontos como atalho."""
    try:
        code = int(rank_code or 0)
    except (TypeError, ValueError):
        return 'Desconhecida'

    # Os códigos são IDs de tier; os pontos ficam separados para não confundir
    # pontos de BR com a patente de CS. O 327 é mantido como Mestre nesta API.
    rank_codes = {
        301: 'Bronze I', 302: 'Bronze II', 303: 'Bronze III',
        304: 'Prata I', 305: 'Prata II', 306: 'Prata III',
        307: 'Ouro I', 308: 'Ouro II', 309: 'Ouro III', 310: 'Ouro IV',
        311: 'Platina I', 312: 'Platina II', 313: 'Platina III', 314: 'Platina IV',
        315: 'Diamante I', 316: 'Diamante II', 317: 'Diamante III', 318: 'Diamante IV',
        319: 'Heroico', 320: 'Heroico Elite',
        321: 'Mestre', 322: 'Mestre Elite',
        323: 'Grão-Mestre I', 324: 'Grão-Mestre II',
        325: 'Grão-Mestre III', 326: 'Grão-Mestre IV',
        327: 'Elite II'
    }
    return rank_codes.get(code, 'Desconhecida')


def normalize_player_info(player_info, requested_uid, region):
    """Converte a resposta do protobuf em um JSON simples e útil para clientes."""
    player_info = player_info or {}
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


@app.route('/api/infor', methods=['GET'])
def api_infor():
    """Consulta informações públicas de um jogador usando apenas region e uid."""
    try:
        region = request.args.get('region', '').upper().strip()
        uid = request.args.get('uid', '').strip()

        if not region:
            return jsonify({
                'success': False,
                'error': 'Missing region',
                'message': "O parâmetro 'region' é obrigatório."
            }), 400

        if not uid:
            return jsonify({
                'success': False,
                'error': 'Missing uid',
                'message': "O parâmetro 'uid' é obrigatório."
            }), 400

        if not uid.isdigit() or int(uid) <= 0:
            return jsonify({
                'success': False,
                'error': 'Invalid uid',
                'message': "O parâmetro 'uid' deve ser um inteiro positivo."
            }), 400

        if region not in accounts:
            return jsonify({
                'success': False,
                'error': 'Invalid region',
                'message': f"Região '{region}' não encontrada.",
                'available_regions': sorted(accounts.keys())
            }), 400

        credentials = accounts[region]
        garena_token = get_garena_token(credentials['uid'], credentials['password'])
        if not garena_token or 'access_token' not in garena_token or 'open_id' not in garena_token:
            return jsonify({
                'success': False,
                'error': 'Garena authentication failed',
                'message': 'Não foi possível autenticar a conta guest da região.'
            }), 401

        major_login = get_major_login(garena_token['access_token'], garena_token['open_id'])
        if not major_login or 'serverUrl' not in major_login or 'token' not in major_login:
            return jsonify({
                'success': False,
                'error': 'Major login failed',
                'message': 'Não foi possível iniciar a sessão do servidor do jogo.'
            }), 502

        player_info = get_player_personal_show(
            major_login['serverUrl'],
            major_login['token'],
            int(uid),
            False,
            7,
            False,
            False
        )

        if not player_info:
            return jsonify({
                'success': False,
                'error': 'Player data not found',
                'message': 'Nenhuma informação foi encontrada para esse UID.'
            }), 404

        return jsonify(normalize_player_info(player_info, uid, region)), 200

    except Exception as exc:
        print(f"/api/infor error: {type(exc).__name__}: {exc}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'Erro interno ao consultar as informações do jogador.'
        }), 500


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)


@app.route('/api/info', methods=['GET'])
def api_info():
    """Consulta informações públicas de um jogador (alias para /api/infor)."""
    return api_infor()


@app.route('/api/likes', methods=['GET'])
def api_likes():
    """Retorna apenas os likes e informações básicas do jogador."""
    try:
        region = request.args.get('region', '').upper().strip()
        uid = request.args.get('uid', '').strip()
        if not region or not uid:
            return jsonify({'success': False, 'error': 'Missing parameters', 'message': "Parâmetros 'region' e 'uid' são obrigatórios."}), 400
        if not uid.isdigit() or int(uid) <= 0:
            return jsonify({'success': False, 'error': 'Invalid uid', 'message': "O UID deve ser um inteiro positivo."}), 400
        if region not in accounts:
            return jsonify({'success': False, 'error': 'Invalid region', 'message': f"Região '{region}' não encontrada."}), 400
        creds = accounts[region]
        gtoken = get_garena_token(creds['uid'], creds['password'])
        if not gtoken or 'access_token' not in gtoken:
            return jsonify({'success': False, 'error': 'Authentication failed'}), 401
        mlogin = get_major_login(gtoken['access_token'], gtoken['open_id'])
        if not mlogin or 'serverUrl' not in mlogin:
            return jsonify({'success': False, 'error': 'Major login failed'}), 502
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
    """Retorna apenas a bio (assinatura) e informações básicas do jogador."""
    try:
        region = request.args.get('region', '').upper().strip()
        uid = request.args.get('uid', '').strip()
        if not region or not uid:
            return jsonify({'success': False, 'error': 'Missing parameters', 'message': "Parâmetros 'region' e 'uid' são obrigatórios."}), 400
        if not uid.isdigit() or int(uid) <= 0:
            return jsonify({'success': False, 'error': 'Invalid uid', 'message': "O UID deve ser um inteiro positivo."}), 400
        if region not in accounts:
            return jsonify({'success': False, 'error': 'Invalid region', 'message': f"Região '{region}' não encontrada."}), 400
        creds = accounts[region]
        gtoken = get_garena_token(creds['uid'], creds['password'])
        if not gtoken or 'access_token' not in gtoken:
            return jsonify({'success': False, 'error': 'Authentication failed'}), 401
        mlogin = get_major_login(gtoken['access_token'], gtoken['open_id'])
        if not mlogin or 'serverUrl' not in mlogin:
            return jsonify({'success': False, 'error': 'Major login failed'}), 502
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
