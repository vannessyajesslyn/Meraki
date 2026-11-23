import time
from datetime import datetime, date
import streamlit as st

from assignment_tracker import AssignmentTracker, DATE_FORMAT
from project_manager import ProjectManager
from storage import load_json, save_json

st.set_page_config(page_title="Meraki", page_icon="🫐", layout="centered")
st.image("assets/homepage.png", width="stretch")
st.title("Meraki")

tab1, tab2, tab3 = st.tabs(["📝 Assignments", "📁 Projects", "⏱️ Study Timer"])

# ==========================================
# TAB 1: ASSIGNMENT TRACKER (Your Exact Class)
# ==========================================
with tab1:
    st.subheader("Assignment Tracker")
    tracker = AssignmentTracker()

    with st.form("add_assignment_form", clear_on_submit=True):
        title = st.text_input("Assignment Title")
        col_d, col_t = st.columns(2)
        due_date = col_d.date_input("Deadline Date")
        due_time = col_t.time_input("Deadline Time")
        desc = st.text_input("Description (optional)")

        if st.form_submit_button("Add Assignment") and title.strip():
            deadline_str = f"{due_date.strftime('%Y-%m-%d')} {due_time.strftime('%H:%M')}"
            tracker.add(title.strip(), deadline_str, desc.strip())
            st.rerun()

    if not tracker.assignments:
        st.info("No assignments yet. Add one above!")
    else:
        for i, a in enumerate(tracker.assignments):
            c1, c2, c3 = st.columns([0.65, 0.25, 0.10])
            label = f"**{a.title}**" + (f" — {a.description}" if a.description else "")
            checked = c1.checkbox(label, value=a.done, key=f"assign_{i}")
            if checked != a.done:
                tracker.toggle_done(i)
                st.rerun()

            status_text = a.time_left_text()
            if a.is_urgent():
                c2.warning(status_text)
            elif status_text == "Overdue!":
                c2.error(status_text)
            else:
                c2.caption(status_text)

            if c3.button("🗑️", key=f"del_assign_{i}"):
                tracker.remove(i)
                st.rerun()

# ==========================================
# TAB 2: PROJECT MANAGER (Your Exact Class)
# ==========================================
with tab2:
    st.subheader("Project Manager")
    pm = ProjectManager()

    with st.form("add_project_form", clear_on_submit=True):
        proj_name = st.text_input("New Project Name")
        if st.form_submit_button("Create Project") and proj_name.strip():
            pm.add_project(proj_name.strip())
            st.rerun()

    if not pm.projects:
        st.info("No projects yet. Create one above!")
    else:
        for p_idx, proj in enumerate(pm.projects):
            with st.expander(f"📁 {proj.name} — {proj.progress_text()}", expanded=True):
                st.progress(proj.progress())

                for s_idx, sub in enumerate(proj.subtasks):
                    sc1, sc2 = st.columns([0.88, 0.12])
                    sub_done = sc1.checkbox(sub["name"], value=sub["done"], key=f"sub_{p_idx}_{s_idx}")
                    if sub_done != sub["done"]:
                        proj.toggle_subtask(s_idx)
                        pm.save()
                        st.rerun()
                    if sc2.button("✕", key=f"del_sub_{p_idx}_{s_idx}"):
                        proj.remove_subtask(s_idx)
                        pm.save()
                        st.rerun()

                with st.form(f"add_sub_{p_idx}", clear_on_submit=True):
                    new_sub = st.text_input("Add subtask", label_visibility="collapsed", placeholder="New subtask...")
                    if st.form_submit_button("Add Subtask") and new_sub.strip():
                        proj.add_subtask(new_sub.strip())
                        pm.save()
                        st.rerun()

                if st.button("Delete Project", key=f"del_proj_{p_idx}"):
                    pm.remove_project(p_idx)
                    st.rerun()

# ==========================================
# TAB 3: STUDY TIMER (50/10/20 Pomodoro Cycle)
# ==========================================
with tab3:
    CYCLE = [
        ("Focus Time", 50 * 60, "Session 1/2"),
        ("Short Break", 10 * 60, "Rest up"),
        ("Focus Time", 50 * 60, "Session 2/2"),
        ("Long Break", 20 * 60, "Long rest - you earned it"),
    ]

    if "phase_idx" not in st.session_state:
        st.session_state.phase_idx = 0
        st.session_state.remaining = CYCLE[0][1]
        st.session_state.running = False
        st.session_state.study_streak = 0

    # Load today's stats
    today_str = date.today().isoformat()
    stats = load_json("study_stats.json", {"date": today_str, "studied_seconds": 0, "sessions": 0})
    if stats.get("date") != today_str:
        stats = {"date": today_str, "studied_seconds": 0, "sessions": 0}

    label, total_secs, subtext = CYCLE[st.session_state.phase_idx]
    st.subheader(f"{label} ({subtext})")

    mins_done = stats["studied_seconds"] // 60
    st.caption(f"📊 {mins_done // 60}h {mins_done % 60}m studied today • {stats['sessions']} sessions completed")

    if st.session_state.study_streak >= 2 * 60 * 60:
        st.warning("Take a break for 20 minutes, you deserve it!")

    mins, secs = divmod(st.session_state.remaining, 60)
    st.markdown(f"# ⏳ {mins:02d}:{secs:02d}")
    st.progress(1.0 - (st.session_state.remaining / total_secs))

    b1, b2, b3 = st.columns(3)
    if b1.button("Pause" if st.session_state.running else "Start", width="stretch"):
        st.session_state.running = not st.session_state.running
        st.rerun()
    if b2.button("Skip Phase", width="stretch"):
        st.session_state.running = False
        st.session_state.phase_idx = (st.session_state.phase_idx + 1) % len(CYCLE)
        st.session_state.remaining = CYCLE[st.session_state.phase_idx][1]
        if st.session_state.phase_idx == 3:
            st.session_state.study_streak = 0
        st.rerun()
    if b3.button("Reset", width="stretch"):
        st.session_state.running = False
        st.session_state.remaining = total_secs
        st.rerun()

    if st.session_state.running:
        time.sleep(1)
        if st.session_state.remaining > 0:
            st.session_state.remaining -= 1
            if label == "Focus Time":
                stats["studied_seconds"] += 1
                st.session_state.study_streak += 1
                if st.session_state.remaining % 15 == 0:
                    save_json("study_stats.json", stats)
        else:
            st.session_state.running = False
            if label == "Focus Time":
                stats["sessions"] += 1
                save_json("study_stats.json", stats)
            st.session_state.phase_idx = (st.session_state.phase_idx + 1) % len(CYCLE)
            st.session_state.remaining = CYCLE[st.session_state.phase_idx][1]
        st.rerun()
