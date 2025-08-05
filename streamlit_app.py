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

st.set_page_config(page_title="⚖️ eBay vs AT&T Classroom Game")

st.title("⚖️ eBay vs AT&T Lawsuit Game - Classroom Edition")

# Firebase credentials and config
try:
    firebase_key = st.secrets["firebase_key"]
    database_url = st.secrets["database_url"]
    
    if not firebase_admin._apps:
        cred = credentials.Certificate(json.loads(firebase_key))
        firebase_admin.initialize_app(cred, {
            'databaseURL': database_url
        })
    FIREBASE_ENABLED = True
except KeyError:
    st.error("🔥 Firebase secrets not configured. Please set up firebase_key and database_url in Streamlit secrets.")
    st.info("For local testing, you can run the local version: lawsuit_game_local.py")
    FIREBASE_ENABLED = False
    st.stop()

# Initialize session state
if 'game_phase' not in st.session_state:
    st.session_state.game_phase = 'story'
if 'current_round' not in st.session_state:
    st.session_state.current_round = 1

# Admin section
admin_password = st.text_input("Teacher Password:", type="password")

if admin_password == "teacher123":
    st.header("🎓 Teacher Control Panel")
    
    # Game phase control
    st.subheader("📋 Control Game Phase")
    phases = ['story', 'assign_roles', 'round_play', 'reveal_scores', 'mixing_strategies', 'wrap_up']
    phase_names = ['Step 1: Tell Story', 'Step 2: Assign Roles', 'Step 3: Round Play', 
                   'Step 4: Reveal & Score', 'Step 5: Mixing Strategies', 'Step 6: Wrap-Up']
    
    current_phase_idx = phases.index(st.session_state.game_phase)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("⬅️ Previous Phase") and current_phase_idx > 0:
            st.session_state.game_phase = phases[current_phase_idx - 1]
            st.rerun()
    
    with col2:
        st.write(f"**Current: {phase_names[current_phase_idx]}**")
    
    with col3:
        if st.button("➡️ Next Phase") and current_phase_idx < len(phases) - 1:
            st.session_state.game_phase = phases[current_phase_idx + 1]
            st.rerun()
    
    # Round control
    st.subheader("🔄 Round Control")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Start New Round"):
            st.session_state.current_round += 1
            # Clear round data
            db.reference(f"classroom_round_{st.session_state.current_round}").delete()
            st.success(f"Started Round {st.session_state.current_round}")
    
    with col2:
        st.write(f"**Current Round: {st.session_state.current_round}**")
    
    with col3:
        if st.button("📊 Show Round Results"):
            st.session_state.show_results = True
    
    # Data management
    st.subheader("🗂️ Data Management")
    if st.button("🗑️ Clear All Game Data"):
        for i in range(1, 11):  # Clear up to 10 rounds
            db.reference(f"classroom_round_{i}").delete()
        db.reference("classroom_players").delete()
        st.success("All game data cleared!")
    
    st.divider()

# Main game phases
if st.session_state.game_phase == 'story':
    st.header("📖 Step 1: The Story")
    st.markdown("""
    ## 🎭 The Legal Drama
    
    **AT&T sues eBay for patent infringement.**
    
    Sometimes eBay is **guilty**, sometimes **innocent**.
    
    eBay can make a **generous offer** or a **stingy offer** to settle out of court.
    
    - If it's **generous**, AT&T always takes it (who wouldn't want more money?).
    - If it's **stingy**, AT&T has a choice: **take it** or **reject and go to court**.
    - **Court costs both sides money** - lawyers are expensive!
    
    ---
    
    *Don't worry about probabilities or equations yet - just think about the choices each side faces.*
    """)
    
    if admin_password == "teacher123":
        st.info("👨‍🏫 **Teacher Note:** This is the narrative phase. Students should understand the basic situation before seeing any math.")

elif st.session_state.game_phase == 'assign_roles':
    st.header("🎭 Step 2: Choose Your Role")
    
    name = st.text_input("Enter your name:")
    
    if name:
        # Register player
        player_ref = db.reference(f"classroom_players/{name}")
        player_data = player_ref.get()
        
        if not player_data:
            role = st.selectbox("Choose your role:", ["eBay", "AT&T"])
            
            if st.button("Join Game"):
                # Assign guilt status if eBay (25% chance of guilty)
                guilt_status = None
                card_color = None
                if role == "eBay":
                    is_guilty = random.random() < 0.25
                    guilt_status = "Guilty" if is_guilty else "Innocent"
                    card_color = "🔴 Red Card" if is_guilty else "🔵 Blue Card"
                
                player_ref.set({
                    "name": name,
                    "role": role,
                    "guilt_status": guilt_status,
                    "card_color": card_color,
                    "timestamp": time.time()
                })
                st.success(f"✅ You are registered as {role}!")
                if role == "eBay":
                    st.success(f"🎴 You drew: {card_color} - You are {guilt_status}")
                st.rerun()
        else:
            role = player_data["role"]
            st.success(f"✅ Welcome back, {name}! You are {role}")
            if role == "eBay":
                st.info(f"🎴 Your card: {player_data['card_color']} - You are {player_data['guilt_status']}")
    
    # Show current players
    if admin_password == "teacher123":
        st.subheader("👥 Current Players")
        players = db.reference("classroom_players").get() or {}
        ebay_players = [p for p in players.values() if p["role"] == "eBay"]
        att_players = [p for p in players.values() if p["role"] == "AT&T"]
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**eBay Players ({len(ebay_players)}):**")
            for player in ebay_players:
                guilt = player.get("guilt_status", "Unknown")
                st.write(f"- {player['name']} ({guilt})")
        
        with col2:
            st.write(f"**AT&T Players ({len(att_players)}):**")
            for player in att_players:
                st.write(f"- {player['name']}")

elif st.session_state.game_phase == 'round_play':
    st.header(f"🎮 Step 3: Round {st.session_state.current_round} - Make Your Moves")
    
    name = st.text_input("Enter your name:")
    
    if name:
        player_ref = db.reference(f"classroom_players/{name}")
        player_data = player_ref.get()
        
        if not player_data:
            st.error("❌ You need to register first! Go back to Step 2.")
        else:
            role = player_data["role"]
            round_ref = db.reference(f"classroom_round_{st.session_state.current_round}/{name}")
            round_data = round_ref.get()
            
            if role == "eBay":
                guilt_status = player_data["guilt_status"]
                st.info(f"🎴 You are: **{guilt_status}**")
                
                if not round_data:
                    if guilt_status == "Innocent":
                        st.warning("⚠️ **Rule**: As an innocent party, you cannot make a Generous offer (it would look suspicious!)")
                        offer = st.radio("Choose your offer:", ["Stingy"])
                    else:  # Guilty
                        offer = st.radio("Choose your offer:", ["Generous", "Stingy"])
                    
                    if st.button("Submit Offer"):
                        round_ref.set({
                            "role": role,
                            "guilt_status": guilt_status,
                            "offer": offer,
                            "timestamp": time.time()
                        })
                        st.success(f"✅ You offered a {offer} settlement!")
                        st.rerun()
                else:
                    st.success(f"✅ You already submitted: {round_data['offer']} offer")
            
            elif role == "AT&T":
                if not round_data:
                    st.info("👀 Waiting to see eBay offers...")
                    
                    # Show available offers to respond to
                    round_offers = db.reference(f"classroom_round_{st.session_state.current_round}").get() or {}
                    ebay_offers = {name: data for name, data in round_offers.items() 
                                 if data.get("role") == "eBay" and "offer" in data}
                    
                    if ebay_offers:
                        st.subheader("📋 eBay Offers Available:")
                        selected_ebay = st.selectbox("Choose an eBay player to respond to:", 
                                                   list(ebay_offers.keys()))
                        
                        if selected_ebay:
                            offer = ebay_offers[selected_ebay]["offer"]
                            st.info(f"💼 {selected_ebay} offered a **{offer}** settlement")
                            
                            if offer == "Generous":
                                st.success("💰 It's generous! You automatically Accept!")
                                response = "Accept"
                                auto_accept = True
                            else:  # Stingy
                                response = st.radio("What do you do?", ["Accept", "Reject (Go to Court)"])
                                auto_accept = False
                            
                            if st.button("Submit Response") or auto_accept:
                                response_final = "Accept" if response == "Accept" else "Reject"
                                round_ref.set({
                                    "role": role,
                                    "responding_to": selected_ebay,
                                    "ebay_offer": offer,
                                    "response": response_final,
                                    "timestamp": time.time()
                                })
                                st.success(f"✅ You chose to {response_final}!")
                                st.rerun()
                    else:
                        st.info("⏳ No eBay offers yet. Waiting for eBay players to make their moves...")
                else:
                    st.success(f"✅ You responded to {round_data['responding_to']}: {round_data['response']}")

elif st.session_state.game_phase == 'reveal_scores':
    st.header(f"📊 Step 4: Round {st.session_state.current_round} Results")
    
    # Show payoff table first
    st.subheader("💰 Payoff Table")
    payoff_data = [
        ["Outcome", "eBay Payoff", "AT&T Payoff"],
        ["Guilty + Generous + Accept", "-100", "+100"],
        ["Guilty + Stingy + Accept", "-20", "+20"],
        ["Guilty + Stingy + Reject", "-200", "+100"],
        ["Innocent + Generous + Accept", "-80", "+100"],
        ["Innocent + Stingy + Accept", "-10", "+20"],
        ["Innocent + Stingy + Reject", "0", "-100"]
    ]
    
    df = pd.DataFrame(payoff_data[1:], columns=payoff_data[0])
    st.table(df)
    
    # Show round results
    round_data = db.reference(f"classroom_round_{st.session_state.current_round}").get() or {}
    
    if round_data:
        st.subheader(f"🎯 Round {st.session_state.current_round} Outcomes:")
        
        # Match eBay and AT&T responses
        ebay_players = {name: data for name, data in round_data.items() if data.get("role") == "eBay"}
        att_responses = {name: data for name, data in round_data.items() if data.get("role") == "AT&T"}
        
        results = []
        for att_name, att_data in att_responses.items():
            ebay_name = att_data.get("responding_to")
            if ebay_name in ebay_players:
                ebay_data = ebay_players[ebay_name]
                
                # Calculate payoffs
                guilt = ebay_data["guilt_status"]
                offer = ebay_data["offer"]
                response = att_data["response"]
                
                if guilt == "Guilty":
                    if offer == "Generous" and response == "Accept":
                        ebay_payoff, att_payoff = -100, 100
                    elif offer == "Stingy" and response == "Accept":
                        ebay_payoff, att_payoff = -20, 20
                    else:  # Stingy + Reject
                        ebay_payoff, att_payoff = -200, 100
                else:  # Innocent
                    if offer == "Generous" and response == "Accept":
                        ebay_payoff, att_payoff = -80, 100
                    elif offer == "Stingy" and response == "Accept":
                        ebay_payoff, att_payoff = -10, 20
                    else:  # Stingy + Reject
                        ebay_payoff, att_payoff = 0, -100
                
                results.append({
                    "eBay Player": ebay_name,
                    "AT&T Player": att_name,
                    "eBay Status": guilt,
                    "Offer": offer,
                    "Response": response,
                    "eBay Payoff": ebay_payoff,
                    "AT&T Payoff": att_payoff
                })
        
        if results:
            results_df = pd.DataFrame(results)
            st.table(results_df)
            
            # Summary statistics
            st.subheader("📈 Round Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                generous_count = len([r for r in results if r["Offer"] == "Generous"])
                st.metric("Generous Offers", generous_count)
            with col2:
                accept_count = len([r for r in results if r["Response"] == "Accept"])
                st.metric("Accepted Offers", accept_count)
            with col3:
                court_count = len([r for r in results if r["Response"] == "Reject"])
                st.metric("Went to Court", court_count)
        else:
            st.info("No completed matches in this round yet.")
    else:
        st.info("No data for this round yet.")

elif st.session_state.game_phase == 'mixing_strategies':
    st.header("🎲 Step 5: Mixed Strategies")
    
    st.markdown("""
    ## 🤔 What You've Learned So Far
    
    After playing several rounds, you might notice:
    - **eBay** sometimes wants to "pool" (always be stingy) or "separate" (generous when guilty)
    - **AT&T** sometimes wants to accept stingy offers, sometimes reject
    
    ## 🎯 The Challenge
    
    Can you find the **mixed strategy** where neither side wants to change their approach?
    
    This is called a **Nash Equilibrium** - where everyone is happy with their strategy given what others are doing.
    """)
    
    # Show theoretical equilibrium
    st.subheader("🧮 The Theory Says...")
    col1, col2 = st.columns(2)
    with col1:
        st.info("""
        **eBay's Optimal Mix:**
        - Use Pooling (always stingy): **3/7 ≈ 42.86%**
        - Use Separating: **4/7 ≈ 57.14%**
        """)
    with col2:
        st.info("""
        **AT&T's Optimal Mix:**
        - Accept Stingy offers: **2/5 = 40%**
        - Reject Stingy offers: **3/5 = 60%**
        """)
    
    # Compare with actual results
    if st.button("📊 Compare with Your Results"):
        all_rounds_data = []
        for round_num in range(1, st.session_state.current_round + 1):
            round_data = db.reference(f"classroom_round_{round_num}").get() or {}
            for name, data in round_data.items():
                if data.get("role") == "eBay":
                    # Determine strategy
                    guilt = data["guilt_status"]
                    offer = data["offer"]
                    if guilt == "Innocent" and offer == "Stingy":
                        strategy = "Separating"
                    elif guilt == "Guilty" and offer == "Generous":
                        strategy = "Separating"
                    else:
                        strategy = "Pooling"
                    
                    all_rounds_data.append({
                        "Round": round_num,
                        "Player": name,
                        "Role": "eBay",
                        "Strategy": strategy,
                        "Offer": offer,
                        "Guilt": guilt
                    })
                elif data.get("role") == "AT&T" and data.get("ebay_offer") == "Stingy":
                    all_rounds_data.append({
                        "Round": round_num,
                        "Player": name,
                        "Role": "AT&T",
                        "Response": data["response"],
                        "Offer_Type": "Stingy"
                    })
        
        if all_rounds_data:
            # Calculate actual percentages
            ebay_data = [d for d in all_rounds_data if d["Role"] == "eBay"]
            att_stingy_data = [d for d in all_rounds_data if d["Role"] == "AT&T" and d["Offer_Type"] == "Stingy"]
            
            if ebay_data:
                pooling_count = len([d for d in ebay_data if d["Strategy"] == "Pooling"])
                pooling_pct = pooling_count / len(ebay_data) * 100
                
                st.subheader("🎯 Your Class Results vs Theory")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("eBay Pooling Strategy", f"{pooling_pct:.1f}%", f"Theory: 42.9%")
                
                if att_stingy_data:
                    accept_count = len([d for d in att_stingy_data if d["Response"] == "Accept"])
                    accept_pct = accept_count / len(att_stingy_data) * 100
                    with col2:
                        st.metric("AT&T Accept Stingy", f"{accept_pct:.1f}%", f"Theory: 40%")

elif st.session_state.game_phase == 'wrap_up':
    st.header("🎓 Step 6: Wrap-Up & Insights")
    
    st.markdown("""
    ## 🧠 What You've Discovered
    
    Through playing this game, you've experienced:
    
    ### 1. **Semi-Separating Equilibrium**
    - eBay can't always separate (guilty=generous, innocent=stingy) because AT&T would learn too much
    - eBay can't always pool (always stingy) because then guilty parties get away too easily
    - The solution: **mix strategies** to keep the other side guessing!
    
    ### 2. **Belief Updating (Bayes' Rule)**
    - When AT&T sees a **Stingy** offer, what's the chance eBay is guilty?
    - **Surprise**: It's only **12.5%**! Most stingy offers come from innocent parties.
    
    ### 3. **Nash Equilibrium in Practice**
    - Your class results should be close to the theoretical prediction
    - eBay: 42.9% pooling strategy
    - AT&T: 40% acceptance of stingy offers
    """)
    
    # Bayesian updating calculation
    st.subheader("🔍 Belief Updating Exercise")
    st.markdown("""
    **Question**: If you see a Stingy offer, what's the probability eBay is guilty?
    
    **Answer**: Using Bayes' Rule...
    - P(Guilty) = 25% (prior)
    - P(Stingy|Guilty) in equilibrium ≈ 43% (pooling probability)  
    - P(Stingy|Innocent) = 100% (innocent always offers stingy)
    
    **Result**: P(Guilty|Stingy) = **12.5%**
    
    *This means even when you see a stingy offer, eBay is probably innocent!*
    """)
    
    # Final class statistics
    st.subheader("📊 Final Class Statistics")
    
    # Aggregate all rounds
    total_games = 0
    total_ebay_payoff = 0
    total_att_payoff = 0
    all_outcomes = []
    
    for round_num in range(1, st.session_state.current_round + 1):
        round_data = db.reference(f"classroom_round_{round_num}").get() or {}
        att_responses = {name: data for name, data in round_data.items() if data.get("role") == "AT&T"}
        
        for att_name, att_data in att_responses.items():
            ebay_name = att_data.get("responding_to")
            if ebay_name in round_data:
                ebay_data = round_data[ebay_name]
                guilt = ebay_data["guilt_status"]
                offer = ebay_data["offer"]
                response = att_data["response"]
                
                # Calculate payoffs (same logic as before)
                if guilt == "Guilty":
                    if offer == "Generous" and response == "Accept":
                        ebay_payoff, att_payoff = -100, 100
                    elif offer == "Stingy" and response == "Accept":
                        ebay_payoff, att_payoff = -20, 20
                    else:
                        ebay_payoff, att_payoff = -200, 100
                else:
                    if offer == "Generous" and response == "Accept":
                        ebay_payoff, att_payoff = -80, 100
                    elif offer == "Stingy" and response == "Accept":
                        ebay_payoff, att_payoff = -10, 20
                    else:
                        ebay_payoff, att_payoff = 0, -100
                
                total_games += 1
                total_ebay_payoff += ebay_payoff
                total_att_payoff += att_payoff
                all_outcomes.append({
                    "guilt": guilt,
                    "offer": offer,
                    "response": response
                })
    
    if total_games > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Games Played", total_games)
        with col2:
            avg_ebay = total_ebay_payoff / total_games
            st.metric("eBay Avg Payoff", f"{avg_ebay:.1f}", "Theory: -56")
        with col3:
            avg_att = total_att_payoff / total_games
            st.metric("AT&T Avg Payoff", f"{avg_att:.1f}", "Theory: 45.7")
    
    st.success("🎉 Congratulations! You've experienced game theory in action!")

# Show current game state for all users
st.sidebar.header("🎮 Game Status")
st.sidebar.write(f"**Phase**: {st.session_state.game_phase.replace('_', ' ').title()}")
st.sidebar.write(f"**Round**: {st.session_state.current_round}")

# Navigation for students
if admin_password != "teacher123":
    st.sidebar.markdown("---")
    st.sidebar.write("**For students**: Enter your name in each phase to participate!")
    st.sidebar.write("**Teacher controls the game phases**")
