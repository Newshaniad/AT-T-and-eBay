# Check if player already has role assigned
existing_player = player_ref.get()
if not existing_player or "role" not in existing_player:
        # Auto-assign roles fairly
        current_players = db.reference("lawsuit_players").get() or {}
        ebay_count = len([p for p in current_players.values() if p and p.get("role") == "eBay"])
        att_count = len([p for p in current_players.values() if p and p.get("role") == "AT&T"])
        # Auto-assign roles fairly with safe handling
        try:
            current_players_raw = db.reference("lawsuit_players").get()
            current_players = current_players_raw if isinstance(current_players_raw, dict) else {}
        except:
            current_players = {}
        
        ebay_count = 0
        att_count = 0
        
        for player in current_players.values():
            if player and isinstance(player, dict):
                role = player.get("role")
                if role == "eBay":
                    ebay_count += 1
                elif role == "AT&T":
                    att_count += 1

# Assign role to balance teams
if ebay_count < (expected_players // 2):
@@ -471,14 +484,18 @@ def plot_enhanced_percentage_bar(choices, labels, title, player_type):
break

if not player_match_id:
        # Find a match
        all_lawsuit_players = db.reference("lawsuit_players").get() or {}
        # Find a match with safe handling
        try:
            all_lawsuit_players_raw = db.reference("lawsuit_players").get()
            all_lawsuit_players = all_lawsuit_players_raw if isinstance(all_lawsuit_players_raw, dict) else {}
        except:
            all_lawsuit_players = {}

if role == "eBay":
# Find an unmatched AT&T player
unmatched_att_players = []
for player_name, player_data in all_lawsuit_players.items():
                if player_data.get("role") == "AT&T" and player_name != name:
                if player_data and isinstance(player_data, dict) and player_data.get("role") == "AT&T" and player_name != name:
# Check if this AT&T player is already matched
already_matched = False
for match_data in all_matches.values():
@@ -504,7 +521,7 @@ def plot_enhanced_percentage_bar(choices, labels, title, player_type):
# Find an unmatched eBay player
unmatched_ebay_players = []
for player_name, player_data in all_lawsuit_players.items():
                if player_data.get("role") == "eBay" and player_name != name:
                if player_data and isinstance(player_data, dict) and player_data.get("role") == "eBay" and player_name != name:
# Check if this eBay player is already matched
already_matched = False
for match_data in all_matches.values():
@@ -818,8 +835,14 @@ def plot_enhanced_percentage_bar(choices, labels, title, player_type):

# Show game status
st.sidebar.header("🎮 Game Status")
players = db.reference("lawsuit_players").get() or {}
expected = db.reference("lawsuit_expected_players").get() or 0
try:
    players_raw = db.reference("lawsuit_players").get()
    players = players_raw if isinstance(players_raw, dict) else {}
    expected = db.reference("lawsuit_expected_players").get() or 0
except:
    players = {}
    expected = 0

registered = len(players)

st.sidebar.write(f"**Players**: {registered}/{expected}")
