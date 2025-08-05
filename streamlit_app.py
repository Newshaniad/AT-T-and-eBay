import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
import time
import random
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64

st.set_page_config(page_title="⚖️ eBay vs AT&T Lawsuit Game")

st.title("⚖️ eBay vs AT&T Lawsuit Game Theory Simulation")

# Game description
st.markdown("""
## Game Description
This game simulates a legal settlement negotiation between eBay and AT&T.

**The Setup:**
- eBay may be **Guilty** (25% chance) or **Innocent** (75% chance)
- eBay can offer either a **Generous** or **Stingy** settlement
- AT&T can **Accept** or **Reject** the settlement offer
- If AT&T rejects, both parties go to court (costly for both)

**eBay's Strategies:**
- **Pooling (SS)**: Always offer Stingy settlement regardless of guilt
- **Separating (SG)**: Offer Stingy if innocent, Generous if guilty

**Nash Equilibrium:**
- eBay uses Pooling strategy with probability **p = 3/7** ≈ 42.86%
- AT&T accepts Stingy offers with probability **q = 2/5** = 40%

**Expected Payoffs at Equilibrium:**
- eBay: -56 points
- AT&T: 320/7 ≈ 45.71 points
""")

# Firebase credentials and config
firebase_key = st.secrets["firebase_key"]
database_url = st.secrets["database_url"]

if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(firebase_key))
    firebase_admin.initialize_app(cred, {
        'databaseURL': database_url
    })

# Password protection
admin_password = st.text_input("Admin Password (for game management):", type="password")

if admin_password == "admin123":
    st.header("🔒 Admin Section")
    
    # Set expected number of players
    st.subheader("👥 Game Configuration")
    current_expected = db.reference("lawsuit_expected_players").get() or 0
    st.write(f"Current expected players: {current_expected}")
    
    new_expected_players = st.number_input(
        "Set expected number of players:", 
        min_value=0, 
        max_value=100, 
        value=current_expected,
        step=2,
        help="Must be an even number (players are paired as eBay vs AT&T)"
    )
    
    if st.button("⚙ Update Expected Players"):
        if new_expected_players % 2 == 0:
            db.reference("lawsuit_expected_players").set(new_expected_players)
            st.success(f"✅ Expected players set to {new_expected_players}")
        else:
            st.error("⚠ Number of players must be even (for pairing)")
    
    # Database cleanup
    if st.button("🗑 Delete ALL Lawsuit Game Data"):
        db.reference("lawsuit_games").delete()
        db.reference("lawsuit_matches").delete()
        db.reference("lawsuit_players").delete()
        db.reference("lawsuit_expected_players").set(0)
        st.success("🧹 ALL lawsuit game data deleted from Firebase.")

if (db.reference("lawsuit_expected_players").get() or 0) <= 0:
    st.stop()

# Initialize game variables
already_matched = False
match_id = None
role = None
pair = None

name = st.text_input("Enter your name to join the lawsuit game:")

if name:
    st.success(f"👋 Welcome, {name}!")

    player_ref = db.reference(f"lawsuit_players/{name}")
    player_data = player_ref.get()

    if not player_data:
        player_ref.set({
            "joined": True,
            "timestamp": time.time()
        })
        st.write("✅ Firebase is connected and you are registered.")

    match_ref = db.reference("lawsuit_matches")
    match_data = match_ref.get() or {}

    # Check if player already matched
    already_matched = False
    for match_id, info in match_data.items():
        if name in info.get("players", []):
            role = "eBay" if info["players"][0] == name else "AT&T"
            st.success(f"⚖️ Hello, {name}! You are playing as {role} in match {match_id}")
            already_matched = True
            break

    if not already_matched:
        # Check if all expected players have finished
        expected_players_ref = db.reference("lawsuit_expected_players")
        expected_players = expected_players_ref.get() or 0
        all_games = db.reference("lawsuit_games").get() or {}
        
        completed_players = 0
        for match_id, game_data in all_games.items():
            if "completed" in game_data and game_data["completed"]:
                completed_players += 2
        
        if expected_players > 0 and completed_players >= expected_players:
            st.info("🎯 All games have been completed! No more matches are available.")
            st.info("📊 Check the Game Summary section below to see the results.")
        else:
            # Get fresh data to avoid race conditions
            players_data = db.reference("lawsuit_players").get() or {}
            match_data = db.reference("lawsuit_matches").get() or {}
            
            unmatched = [p for p in players_data.keys()
                         if not any(p in m.get("players", []) for m in match_data.values())
                         and p != name]

            if unmatched:
                partner = unmatched[0]
                pair = sorted([name, partner])
                match_id = f"{pair[0]}_vs_{pair[1]}"
                
                # Double-check that match doesn't exist
                existing_match = match_ref.child(match_id).get()
                if not existing_match:
                    match_ref.child(match_id).set({"players": pair})
                    role = "eBay" if pair[0] == name else "AT&T"
                    st.success(f"⚖️ Hello, {name}! You are playing as {role} in match {match_id}")
                else:
                    role = "eBay" if existing_match["players"][0] == name else "AT&T"
                    st.success(f"⚖️ Hello, {name}! You are playing as {role} in match {match_id}")
                    already_matched = True
            else:
                st.info("⏳ Waiting for another player to join...")
                with st.spinner("Checking for match..."):
                    timeout = 30
                    for i in range(timeout):
                        match_data = match_ref.get() or {}
                        for match_id, info in match_data.items():
                            if name in info.get("players", []):
                                role = "eBay" if info["players"][0] == name else "AT&T"
                                st.success(f"⚖️ Hello, {name}! You are playing as {role} in match {match_id}")
                                already_matched = True
                                st.rerun()
                        time.sleep(2)

    # Game Logic
    if already_matched or role is not None:
        match_id = match_id if already_matched else f"{pair[0]}_vs_{pair[1]}"
        role = role if already_matched else ("eBay" if pair[0] == name else "AT&T")
        game_ref = db.reference(f"lawsuit_games/{match_id}")

        # Check if game is already completed
        game_data = game_ref.get() or {}
        if game_data.get("completed", False):
            st.success("🎉 This game has been completed!")
            
            # Display results
            ebay_guilt = "Guilty" if game_data.get("ebay_is_guilty", False) else "Innocent"
            ebay_strategy = game_data.get("ebay_strategy", "Unknown")
            ebay_offer = game_data.get("ebay_offer", "Unknown")
            att_response = game_data.get("att_response", "Unknown")
            ebay_payoff = game_data.get("ebay_payoff", 0)
            att_payoff = game_data.get("att_payoff", 0)
            
            st.markdown(f"""
            ### Game Results:
            - **eBay was**: {ebay_guilt}
            - **eBay's strategy**: {ebay_strategy}
            - **eBay's offer**: {ebay_offer}
            - **AT&T's response**: {att_response}
            - **eBay's payoff**: {ebay_payoff}
            - **AT&T's payoff**: {att_payoff}
            """)
        else:
            # Start the game
            st.subheader("🎮 Game in Progress")
            
            if role == "eBay":
                st.markdown("### You are eBay")
                
                # Check if eBay has made their moves
                if not game_data.get("ebay_moves_made", False):
                    # Determine guilt (if not already set)
                    if "ebay_is_guilty" not in game_data:
                        ebay_is_guilty = random.random() < 0.25  # 25% chance
                        game_ref.update({"ebay_is_guilty": ebay_is_guilty})
                    else:
                        ebay_is_guilty = game_data["ebay_is_guilty"]
                    
                    guilt_status = "Guilty" if ebay_is_guilty else "Innocent"
                    st.info(f"🎯 You are: **{guilt_status}**")
                    
                    # Choose strategy
                    strategy = st.radio(
                        "Choose your strategy:",
                        ["Pooling (SS) - Always offer Stingy", "Separating (SG) - Stingy if innocent, Generous if guilty"]
                    )
                    
                    if st.button("Submit Strategy"):
                        strategy_short = "SS" if "Pooling" in strategy else "SG"
                        
                        # Determine offer based on strategy
                        if strategy_short == "SS":
                            offer = "Stingy"
                        else:  # SG strategy
                            offer = "Generous" if ebay_is_guilty else "Stingy"
                        
                        game_ref.update({
                            "ebay_strategy": strategy_short,
                            "ebay_offer": offer,
                            "ebay_moves_made": True,
                            "timestamp": time.time()
                        })
                        st.success(f"✅ You chose {strategy_short} strategy and offered a {offer} settlement!")
                        st.rerun()
                else:
                    st.info("✅ You have submitted your strategy. Waiting for AT&T's response...")
            
            elif role == "AT&T":
                st.markdown("### You are AT&T")
                
                # Wait for eBay's offer
                if not game_data.get("ebay_moves_made", False):
                    st.info("⏳ Waiting for eBay to make their offer...")
                else:
                    ebay_offer = game_data.get("ebay_offer", "Unknown")
                    st.info(f"📋 eBay has offered a **{ebay_offer}** settlement")
                    
                    # Check if AT&T has responded
                    if not game_data.get("att_response_made", False):
                        if ebay_offer == "Generous":
                            st.success("💰 The offer is Generous - you automatically Accept!")
                            game_ref.update({
                                "att_response": "Accept",
                                "att_response_made": True,
                                "timestamp": time.time()
                            })
                            st.rerun()
                        else:  # Stingy offer
                            response = st.radio(
                                "The offer is Stingy. What do you do?",
                                ["Accept", "Reject (Go to Court)"]
                            )
                            
                            if st.button("Submit Response"):
                                response_short = "Accept" if response == "Accept" else "Reject"
                                game_ref.update({
                                    "att_response": response_short,
                                    "att_response_made": True,
                                    "timestamp": time.time()
                                })
                                st.success(f"✅ You chose to {response_short}!")
                                st.rerun()
                    else:
                        att_response = game_data.get("att_response", "Unknown")
                        st.info(f"✅ You chose to {att_response}")

            # Calculate payoffs when both players have moved
            if game_data.get("ebay_moves_made", False) and game_data.get("att_response_made", False) and not game_data.get("completed", False):
                # Calculate payoffs
                ebay_is_guilty = game_data.get("ebay_is_guilty", False)
                ebay_offer = game_data.get("ebay_offer", "Stingy")
                att_response = game_data.get("att_response", "Accept")
                
                # Payoff matrix based on the game description
                if ebay_offer == "Generous" and att_response == "Accept":
                    if ebay_is_guilty:
                        ebay_payoff = -100  # Guilty and generous settlement
                        att_payoff = 100    # Good deal for AT&T
                    else:
                        ebay_payoff = -80   # Innocent but generous settlement
                        att_payoff = 100    # Good deal for AT&T
                elif ebay_offer == "Stingy" and att_response == "Accept":
                    if ebay_is_guilty:
                        ebay_payoff = -20   # Guilty but only stingy settlement
                        att_payoff = 20     # Modest deal for AT&T
                    else:
                        ebay_payoff = -10   # Innocent and stingy settlement
                        att_payoff = 20     # Modest deal for AT&T
                else:  # Reject - go to court
                    court_costs = 50
                    if ebay_is_guilty:
                        ebay_payoff = -150 - court_costs  # Lose case and pay court costs
                        att_payoff = 150 - court_costs    # Win case but pay court costs
                    else:
                        ebay_payoff = 50 - court_costs    # Win case but pay court costs
                        att_payoff = -50 - court_costs    # Lose case and pay court costs
                
                # Update game with final results
                game_ref.update({
                    "ebay_payoff": ebay_payoff,
                    "att_payoff": att_payoff,
                    "completed": True,
                    "final_timestamp": time.time()
                })
                
                st.success("🎉 Game Complete!")
                guilt_status = "Guilty" if ebay_is_guilty else "Innocent"
                st.markdown(f"""
                ### Final Results:
                - **eBay was**: {guilt_status}
                - **eBay's offer**: {ebay_offer}
                - **AT&T's response**: {att_response}
                - **eBay's payoff**: {ebay_payoff}
                - **AT&T's payoff**: {att_payoff}
                """)

# Game Summary Section
st.header("📊 Game Summary")

expected_players = db.reference("lawsuit_expected_players").get() or 0
all_games = db.reference("lawsuit_games").get() or {}

completed_games = 0
total_ebay_payoff = 0
total_att_payoff = 0
strategy_counts = {"SS": 0, "SG": 0}
response_counts = {"Accept": 0, "Reject": 0}
guilt_outcomes = {"Guilty": 0, "Innocent": 0}

for match_id, game_data in all_games.items():
    if game_data.get("completed", False):
        completed_games += 1
        total_ebay_payoff += game_data.get("ebay_payoff", 0)
        total_att_payoff += game_data.get("att_payoff", 0)
        
        strategy = game_data.get("ebay_strategy", "Unknown")
        if strategy in strategy_counts:
            strategy_counts[strategy] += 1
            
        response = game_data.get("att_response", "Unknown")
        if response in response_counts:
            response_counts[response] += 1
            
        guilt = "Guilty" if game_data.get("ebay_is_guilty", False) else "Innocent"
        if guilt in guilt_outcomes:
            guilt_outcomes[guilt] += 1

if expected_players > 0 and completed_games * 2 >= expected_players:
    st.success(f"✅ All {expected_players} players completed the game!")
    
    # Display statistics
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Strategy Distribution")
        if completed_games > 0:
            fig, ax = plt.subplots()
            strategies = list(strategy_counts.keys())
            counts = list(strategy_counts.values())
            ax.bar(strategies, counts)
            ax.set_title("eBay Strategy Choices")
            ax.set_ylabel("Count")
            st.pyplot(fig)
    
    with col2:
        st.subheader("AT&T Responses to Stingy Offers")
        stingy_responses = {"Accept": 0, "Reject": 0}
        for game_data in all_games.values():
            if game_data.get("completed", False) and game_data.get("ebay_offer") == "Stingy":
                response = game_data.get("att_response", "Unknown")
                if response in stingy_responses:
                    stingy_responses[response] += 1
        
        if sum(stingy_responses.values()) > 0:
            fig, ax = plt.subplots()
            responses = list(stingy_responses.keys())
            counts = list(stingy_responses.values())
            ax.bar(responses, counts)
            ax.set_title("AT&T Responses to Stingy Offers")
            ax.set_ylabel("Count")
            st.pyplot(fig)
    
    # Average payoffs
    if completed_games > 0:
        avg_ebay = total_ebay_payoff / completed_games
        avg_att = total_att_payoff / completed_games
        
        st.subheader("Average Payoffs")
        st.write(f"eBay average payoff: {avg_ebay:.2f}")
        st.write(f"AT&T average payoff: {avg_att:.2f}")
        
        st.subheader("Nash Equilibrium Comparison")
        st.write("**Theoretical Nash Equilibrium:**")
        st.write("- eBay expected payoff: -56")
        st.write("- AT&T expected payoff: 45.71")
        st.write("- eBay should use Pooling (SS) 3/7 ≈ 42.86% of the time")
        st.write("- AT&T should Accept Stingy offers 2/5 = 40% of the time")

elif expected_players > 0:
    st.info(f"⏳ Waiting for all participants to finish... ({completed_games * 2}/{expected_players} players completed)")
else:
    st.info("📈 Admin needs to set the expected number of players to display results.")
