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
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import tempfile
import os

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

# Enhanced PDF generation function
def create_comprehensive_game_report():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.darkblue,
        spaceAfter=30
    )
    story.append(Paragraph("⚖️ AT&T vs eBay Lawsuit Game - Complete Results", title_style))
    story.append(Spacer(1, 20))
    
    # Get all game data
    players_data = db.reference("classroom_players").get() or {}
    current_round = st.session_state.current_round
    
    # Summary section
    story.append(Paragraph(f"<b>Game Summary</b>", styles['Heading2']))
    story.append(Paragraph(f"Current Round: {current_round}", styles['Normal']))
    story.append(Paragraph(f"Total Players: {len(players_data)}", styles['Normal']))
    ebay_count = len([p for p in players_data.values() if p.get("role") == "eBay"])
    att_count = len([p for p in players_data.values() if p.get("role") == "AT&T"])
    story.append(Paragraph(f"eBay Players: {ebay_count}", styles['Normal']))
    story.append(Paragraph(f"AT&T Players: {att_count}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Player roster
    story.append(Paragraph("<b>Player Roster</b>", styles['Heading2']))
    player_table_data = [["Player Name", "Role", "Status", "Card Color"]]
    
    for name, data in players_data.items():
        role = data.get("role", "Unknown")
        guilt_status = data.get("guilt_status", "N/A")
        card_color = data.get("card_color", "N/A")
        player_table_data.append([name, role, guilt_status, card_color])
    
    player_table = Table(player_table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 2*inch])
    player_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(player_table)
    story.append(Spacer(1, 30))
    
    # Round-by-round results
    story.append(Paragraph("<b>Round-by-Round Results</b>", styles['Heading2']))
    
    all_results = []
    total_payoffs = {"eBay": 0, "AT&T": 0}
    
    for round_num in range(1, current_round + 1):
        round_data = db.reference(f"classroom_round_{round_num}").get() or {}
        if not round_data:
            continue
            
        story.append(Paragraph(f"<b>Round {round_num}</b>", styles['Heading3']))
        
        # Process round results
        ebay_players = {name: data for name, data in round_data.items() if data.get("role") == "eBay"}
        att_responses = {name: data for name, data in round_data.items() if data.get("role") == "AT&T"}
        
        round_results = []
        for att_name, att_data in att_responses.items():
            ebay_name = att_data.get("responding_to")
            if ebay_name in ebay_players:
                ebay_data = ebay_players[ebay_name]
                
                guilt = ebay_data["guilt_status"]
                offer = ebay_data["offer"]
                response = att_data["response"]
                
                # Calculate payoffs
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
                
                total_payoffs["eBay"] += ebay_payoff
                total_payoffs["AT&T"] += att_payoff
                
                round_results.append([
                    ebay_name, att_name, guilt, offer, response, 
                    str(ebay_payoff), str(att_payoff)
                ])
                all_results.append({
                    "round": round_num,
                    "guilt": guilt,
                    "offer": offer,
                    "response": response,
                    "ebay_payoff": ebay_payoff,
                    "att_payoff": att_payoff
                })
        
        if round_results:
            round_table_data = [["eBay Player", "AT&T Player", "eBay Status", "Offer", "Response", "eBay Payoff", "AT&T Payoff"]]
            round_table_data.extend(round_results)
            
            round_table = Table(round_table_data, colWidths=[1*inch, 1*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
            round_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(round_table)
        else:
            story.append(Paragraph("No matches in this round.", styles['Normal']))
        story.append(Spacer(1, 15))
    
    # Overall statistics
    story.append(Paragraph("<b>Overall Statistics</b>", styles['Heading2']))
    if all_results:
        total_games = len(all_results)
        generous_offers = len([r for r in all_results if r["offer"] == "Generous"])
        stingy_offers = len([r for r in all_results if r["offer"] == "Stingy"])
        accepted_offers = len([r for r in all_results if r["response"] == "Accept"])
        court_cases = len([r for r in all_results if r["response"] == "Reject"])
        guilty_cases = len([r for r in all_results if r["guilt"] == "Guilty"])
        innocent_cases = len([r for r in all_results if r["guilt"] == "Innocent"])
        
        stats_data = [
            ["Metric", "Count", "Percentage"],
            ["Total Games", str(total_games), "100%"],
            ["Generous Offers", str(generous_offers), f"{generous_offers/total_games*100:.1f}%"],
            ["Stingy Offers", str(stingy_offers), f"{stingy_offers/total_games*100:.1f}%"],
            ["Accepted Settlements", str(accepted_offers), f"{accepted_offers/total_games*100:.1f}%"],
            ["Went to Court", str(court_cases), f"{court_cases/total_games*100:.1f}%"],
            ["Guilty Cases", str(guilty_cases), f"{guilty_cases/total_games*100:.1f}%"],
            ["Innocent Cases", str(innocent_cases), f"{innocent_cases/total_games*100:.1f}%"]
        ]
        
        stats_table = Table(stats_data, colWidths=[2.5*inch, 1*inch, 1.5*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 20))
        
        # Average payoffs
        avg_ebay = total_payoffs["eBay"] / total_games if total_games > 0 else 0
        avg_att = total_payoffs["AT&T"] / total_games if total_games > 0 else 0
        story.append(Paragraph(f"Average eBay Payoff: {avg_ebay:.1f}", styles['Normal']))
        story.append(Paragraph(f"Average AT&T Payoff: {avg_att:.1f}", styles['Normal']))
        story.append(Paragraph("Theoretical eBay Payoff: -56.0", styles['Normal']))
        story.append(Paragraph("Theoretical AT&T Payoff: 45.7", styles['Normal']))
    
    story.append(Spacer(1, 20))
    story.append(Paragraph("✅ Report generated automatically", styles['Normal']))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

# Admin section with comprehensive dashboard
admin_password = st.text_input("Teacher Password:", type="password")

if admin_password == "admin123":
    st.header("🎓 Teacher Control Panel & Analytics Dashboard")
    
    # Get real-time data
    all_players = db.reference("classroom_players").get() or {}
    current_round_data = db.reference(f"classroom_round_{st.session_state.current_round}").get() or {}
    
    # Calculate real-time statistics
    total_players = len(all_players)
    ebay_players = [p for p in all_players.values() if p.get("role") == "eBay"]
    att_players = [p for p in all_players.values() if p.get("role") == "AT&T"]
    guilty_players = [p for p in ebay_players if p.get("guilt_status") == "Guilty"]
    innocent_players = [p for p in ebay_players if p.get("guilt_status") == "Innocent"]
    
    # Current round activity
    current_submissions = len([p for p in current_round_data.values() if "offer" in p or "response" in p])
    ebay_offers = {name: data for name, data in current_round_data.items() if data.get("role") == "eBay"}
    att_responses = {name: data for name, data in current_round_data.items() if data.get("role") == "AT&T"}
    
    # Live Statistics Dashboard
    st.subheader("📊 Live Game Statistics")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Players", total_players)
    with col2:
        st.metric("eBay Players", len(ebay_players))
    with col3:
        st.metric("AT&T Players", len(att_players))
    with col4:
        st.metric("Guilty eBay", len(guilty_players))
    with col5:
        st.metric("Innocent eBay", len(innocent_players))
    
    # Current round progress
    st.subheader(f"🎮 Round {st.session_state.current_round} Progress")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Submissions", current_submissions)
    with col2:
        st.metric("eBay Offers Made", len(ebay_offers))
    with col3:
        st.metric("AT&T Responses", len(att_responses))
    with col4:
        matches_made = len([att_data for att_data in att_responses.values() if att_data.get("responding_to") in ebay_offers])
        st.metric("Completed Matches", matches_made)
    
    # Real-time player activity monitor
    st.subheader("👥 Real-Time Player Activity")
    
    if all_players:
        player_activity = []
        for name, player_data in all_players.items():
            role = player_data.get("role", "Unknown")
            
            # Determine current activity
            activity_status = "🔴 Registered"
            current_activity = "Waiting"
            
            if name in current_round_data:
                round_player_data = current_round_data[name]
                if role == "eBay" and "offer" in round_player_data:
                    activity_status = "🟢 Submitted Offer"
                    current_activity = f"Offered: {round_player_data['offer']}"
                elif role == "AT&T" and "response" in round_player_data:
                    activity_status = "🟢 Submitted Response"
                    current_activity = f"Response: {round_player_data['response']}"
                elif role == "eBay":
                    activity_status = "🟡 In Game"
                    current_activity = "Making offer..."
                else:
                    activity_status = "🟡 In Game"
                    current_activity = "Choosing response..."
            
            # Additional info for eBay players
            extra_info = ""
            if role == "eBay":
                guilt = player_data.get("guilt_status", "Unknown")
                card = player_data.get("card_color", "Unknown")
                extra_info = f"{guilt} ({card})"
            
            player_activity.append({
                "Player Name": name,
                "Role": role,
                "Status": activity_status,
                "Current Activity": current_activity,
                "Extra Info": extra_info
            })
        
        activity_df = pd.DataFrame(player_activity)
        st.dataframe(activity_df, use_container_width=True)
    else:
        st.info("No players registered yet.")
    
    # Live analytics charts
    st.subheader("📈 Live Game Analytics")
    
    # Collect all historical data for charts
    all_historical_data = []
    for round_num in range(1, st.session_state.current_round + 1):
        round_data = db.reference(f"classroom_round_{round_num}").get() or {}
        att_responses = {name: data for name, data in round_data.items() if data.get("role") == "AT&T"}
        
        for att_name, att_data in att_responses.items():
            ebay_name = att_data.get("responding_to")
            if ebay_name in round_data:
                ebay_data = round_data[ebay_name]
                all_historical_data.append({
                    "round": round_num,
                    "guilt": ebay_data["guilt_status"],
                    "offer": ebay_data["offer"],
                    "response": att_data["response"]
                })
    
    # Enhanced chart function
    def plot_lawsuit_chart(data_list, category, title, colors_list):
        if len(data_list) > 0:
            counts = pd.Series(data_list).value_counts(normalize=True) * 100
            
            fig, ax = plt.subplots(figsize=(8, 5))
            fig.patch.set_facecolor('#f8f9fa')
            ax.set_facecolor('#ffffff')
            
            bars = counts.plot(kind='bar', ax=ax, color=colors_list[:len(counts)], linewidth=2, width=0.6)
            
            ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
            ax.set_ylabel("Percentage (%)", fontsize=12)
            ax.set_xlabel(category, fontsize=12)
            ax.tick_params(rotation=45, labelsize=10)
            ax.set_ylim(0, max(100, counts.max() * 1.1))
            
            ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.5)
            
            # Add value labels
            for i, bar in enumerate(ax.patches):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 2,
                       f'{height:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
            
            # Add sample info
            ax.text(0.02, 0.95, f"Total: {len(data_list)} cases", transform=ax.transAxes, 
                   fontsize=9, bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgray', alpha=0.7))
            
            plt.tight_layout()
            return fig
        else:
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.text(0.5, 0.5, f'No data yet for {title}', ha='center', va='center', 
                   fontsize=12, transform=ax.transAxes)
            ax.set_title(title, fontsize=14, fontweight='bold')
            return fig
    
    if all_historical_data:
        col1, col2 = st.columns(2)
        
        with col1:
            offers_data = [d["offer"] for d in all_historical_data]
            fig1 = plot_lawsuit_chart(offers_data, "Offer Type", "eBay Settlement Offers", ['#e74c3c', '#3498db'])
            st.pyplot(fig1)
            
            guilt_data = [d["guilt"] for d in all_historical_data]
            fig3 = plot_lawsuit_chart(guilt_data, "eBay Status", "eBay Guilt Distribution", ['#e74c3c', '#2ecc71'])
            st.pyplot(fig3)
        
        with col2:
            responses_data = [d["response"] for d in all_historical_data]
            fig2 = plot_lawsuit_chart(responses_data, "AT&T Response", "AT&T Responses to Offers", ['#3498db', '#e74c3c'])
            st.pyplot(fig2)
            
            # Strategy analysis
            strategies = []
            for d in all_historical_data:
                if d["guilt"] == "Innocent" and d["offer"] == "Stingy":
                    strategies.append("Separating")
                elif d["guilt"] == "Guilty" and d["offer"] == "Generous":
                    strategies.append("Separating")
                else:
                    strategies.append("Pooling")
            
            if strategies:
                fig4 = plot_lawsuit_chart(strategies, "Strategy", "eBay Strategy Analysis", ['#9b59b6', '#f39c12'])
                st.pyplot(fig4)
    else:
        st.info("No game data available yet. Play some rounds to see analytics!")
    
    # Game phase control
    st.subheader("📋 Game Phase Control")
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
            st.rerun()
    
    with col2:
        st.write(f"**Current Round: {st.session_state.current_round}**")
    
    with col3:
        if st.button("📊 Show Round Results"):
            st.session_state.show_results = True
            st.rerun()
    
    # Enhanced data management
    st.subheader("📄 Reports & Data Management")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        # PDF Download
        if st.button("📄 Download Complete Game Report (PDF)"):
            with st.spinner("Generating comprehensive PDF report..."):
                try:
                    pdf_buffer = create_comprehensive_game_report()
                    b64 = base64.b64encode(pdf_buffer.read()).decode()
                    href = f'<a href="data:application/pdf;base64,{b64}" download="lawsuit_game_results.pdf">Click here to download Complete Game Report</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    st.success("✅ Complete game report generated successfully!")
                except Exception as e:
                    st.error(f"Error generating PDF: {str(e)}")
    
    with col2:
        # Excel export
        if st.button("📊 Export Data to Excel"):
            try:
                # Prepare data for Excel
                excel_data = []
                for round_num in range(1, st.session_state.current_round + 1):
                    round_data = db.reference(f"classroom_round_{round_num}").get() or {}
                    att_responses = {name: data for name, data in round_data.items() if data.get("role") == "AT&T"}
                    
                    for att_name, att_data in att_responses.items():
                        ebay_name = att_data.get("responding_to")
                        if ebay_name in round_data:
                            ebay_data = round_data[ebay_name]
                            excel_data.append({
                                "Round": round_num,
                                "eBay_Player": ebay_name,
                                "ATT_Player": att_name,
                                "eBay_Status": ebay_data["guilt_status"],
                                "Offer": ebay_data["offer"],
                                "Response": att_data["response"],
                                "Timestamp": att_data.get("timestamp", "")
                            })
                
                if excel_data:
                    df = pd.DataFrame(excel_data)
                    excel_buffer = BytesIO()
                    df.to_excel(excel_buffer, index=False)
                    excel_buffer.seek(0)
                    b64 = base64.b64encode(excel_buffer.read()).decode()
                    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="lawsuit_game_data.xlsx">Click here to download Excel file</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    st.success("✅ Excel file generated successfully!")
                else:
                    st.warning("No data available to export.")
            except Exception as e:
                st.error(f"Error generating Excel file: {str(e)}")
    
    with col3:
        # Clear data
        if st.button("🗑️ Clear All Game Data"):
            for i in range(1, 21):  # Clear up to 20 rounds
                db.reference(f"classroom_round_{i}").delete()
            db.reference("classroom_players").delete()
            st.success("🧹 All game data cleared!")
            st.rerun()
    
    # Auto-refresh control
    if st.session_state.game_phase == 'round_play' and len(all_players) > 0:
        # Auto-refresh during active gameplay
        time.sleep(5)
        st.rerun()
    elif st.button("🔄 Manual Refresh Dashboard"):
        st.rerun()
    
    st.divider()
    st.info("👨‍🏫 **Teacher Dashboard**: Monitor student progress, control game flow, and analyze results in real-time.")
    
    # Stop here - admin doesn't participate in the game
    st.stop()

# Main game phases (same as original code)
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
    
    # Show current players (non-admin view)
    st.subheader("👥 Current Players")
    players = db.reference("classroom_players").get() or {}
    ebay_players = [p for p in players.values() if p["role"] == "eBay"]
    att_players = [p for p in players.values() if p["role"] == "AT&T"]
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**eBay Players ({len(ebay_players)}):**")
        for player in ebay_players:
            st.write(f"- {player['name']}")
    
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
st.sidebar.markdown("---")
st.sidebar.write("**For students**: Enter your name in each phase to participate!")
st.sidebar.write("**Teacher controls the game phases**")
