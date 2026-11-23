"""Meraki - browser version. Works on a desktop browser AND on a phone.

Run:  streamlit run web_app.py
      (needs a recent Streamlit, 1.46 or newer: pip install -U streamlit)

It uses the SAME logic files as the desktop app (assignment_tracker.py,
project_manager.py, study_timer.py, storage.py), so both versions behave
the same and share the same save files.

What makes it phone-friendly:
  - a short banner from the homepage picture instead of the full tall image
  - text and the countdown resize with the screen (CSS clamp)
  - each assignment / sub-task row keeps its checkbox and delete button side
    by side, instead of Streamlit stacking them on small screens
  - bigger buttons to tap
  - the timer ticks inside a "fragment", so only the timer refreshes every
    second: the page doesn't jump while you scroll or type on your phone
"""
import os

import streamlit as st
from PIL import Image

import study_timer as stimer
from assignment_tracker import AssignmentTracker
from project_manager import ProjectManager

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
ASSIGNMENTS_FILE = os.path.join(HERE, "assignments.json")
PROJECTS_FILE = os.path.join(HERE, "projects.json")
STATS_FILE = os.path.join(HERE, "study_stats.json")

st.set_page_config(page_title="Meraki", page_icon="🫐", layout="centered",
                   initial_sidebar_state="collapsed")

# ---------------------------------------------------------------- styles
st.markdown("""
<style>
.block-container { padding-top: 1.5rem; max-width: 760px; }
.meraki-title { font-family: Georgia, 'Times New Roman', serif; text-align: center;
                font-size: clamp(2.2rem, 8vw, 3.2rem); color: #54283A; margin: .6rem 0 0; }
.meraki-sub   { text-align: center; color: #8A5A6E; margin: 0 0 .4rem; }
[data-testid="stImage"] img { border-radius: 18px; }

/* timer */
.meraki-phase   { text-align: center; font-weight: 700; color: #54283A; font-size: 1.25rem; margin: 0; }
.meraki-session { text-align: center; color: #8A5A6E; margin: 0; }
.meraki-clock   { text-align: center; font-family: 'Courier New', monospace; font-weight: 700;
                  font-size: clamp(3.4rem, 17vw, 6rem); color: #2B2B36; line-height: 1.1;
                  margin: .2rem 0 .4rem; }

/* rows (assignment, sub-task, timer buttons): keep columns side by side on phones */
div[class*="st-key-row"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; }
div[class*="st-key-row"] [data-testid="stColumn"],
div[class*="st-key-row"] [data-testid="column"] { min-width: 0 !important; }

@media (max-width: 640px) {
  .block-container { padding: 1rem .8rem 3rem; }
  button[data-baseweb="tab"] { padding-left: .55rem; padding-right: .55rem; }
  button[data-baseweb="tab"] p { font-size: .95rem; }
  .stButton button, .stFormSubmitButton button { min-height: 2.75rem; }   /* easy to tap */
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- header
@st.cache_data
def banner():
    """A wide slice of the homepage picture (books, clock, sticky notes)."""
    path = os.path.join(ASSETS, "homepage.png")
    if not os.path.exists(path):
        return None
    im = Image.open(path).convert("RGB")
    w, h = im.size
    top, bottom = int(h * 0.22), int(h * 0.55)          # the shelf, clock and notes
    return im.crop((0, top, w, bottom))


img = banner()
if img is not None:
    st.image(img, width="stretch")
st.markdown("<h1 class='meraki-title'>Meraki</h1>"
            "<p class='meraki-sub'>your cozy study corner</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📝 Assignments", "📁 Projects", "⏱️ Timer"])


def status_line(a):
    """Coloured 'time left' + due date for one assignment."""
    due = a.deadline.strftime("%a %d %b, %H:%M")
    if a.done:
        return f":gray[**done** · due {due}]"
    left = a.time_left_text()
    if left == "Overdue!":
        return f":red[**Overdue!**] · due {due}"
    if a.is_urgent():
        return f":orange[**{left}**] · due {due}"
    return f"**{left}** · due {due}"


# ================================================================ TAB 1: ASSIGNMENTS
with tab1:
    st.subheader("Assignment Tracker")
    tracker = AssignmentTracker(ASSIGNMENTS_FILE)

    with st.form("add_assignment_form", clear_on_submit=True):
        title = st.text_input("Assignment title", placeholder="e.g. Calculus homework")
        col_d, col_t = st.columns(2)
        due_date = col_d.date_input("Due date")
        due_time = col_t.time_input("Due time")
        desc = st.text_input("Notes (optional)")
        if st.form_submit_button("Add assignment", width="stretch", type="primary"):
            if title.strip():
                deadline = f"{due_date.strftime('%Y-%m-%d')} {due_time.strftime('%H:%M')}"
                tracker.add(title.strip(), deadline, desc.strip())
                st.rerun()
            else:
                st.warning("Write the assignment name first.")

    items = tracker.sorted_list()                      # not done first, soonest first
    if not items:
        st.info("No assignments yet. Add one above!")
    else:
        done_count = sum(1 for a in items if a.done)
        st.caption(f"{len(items) - done_count} to do · {done_count} done")
        for a in items:
            i = tracker.assignments.index(a)           # real position, for toggle/remove
            with st.container(border=True, key=f"row_assign_{i}"):
                c1, c2 = st.columns([0.84, 0.16], vertical_alignment="center")
                label = f"~~{a.title}~~" if a.done else f"**{a.title}**"
                checked = c1.checkbox(label, value=a.done, key=f"assign_{i}")
                if checked != a.done:
                    tracker.toggle_done(i)
                    st.rerun()
                if c2.button("🗑️", key=f"del_assign_{i}", help="Delete", width="stretch"):
                    tracker.remove(i)
                    st.rerun()
                st.markdown(status_line(a))
                if a.description:
                    st.caption(a.description)


# ================================================================ TAB 2: PROJECTS
with tab2:
    st.subheader("Project Manager")
    pm = ProjectManager(PROJECTS_FILE)

    with st.form("add_project_form", clear_on_submit=True):
        proj_name = st.text_input("New project", placeholder="e.g. I2P final project")
        if st.form_submit_button("Create project", width="stretch", type="primary"):
            if proj_name.strip():
                pm.add_project(proj_name.strip())
                st.rerun()
            else:
                st.warning("Write a project name first.")

    if not pm.projects:
        st.info("No projects yet. Create one above, then split it into small steps.")
    else:
        for p_idx, proj in enumerate(pm.projects):
            pct = round(proj.progress() * 100)
            badge = " ⭐" if proj.is_complete() else ""
            with st.expander(f"📁 {proj.name} · {pct}%{badge}", expanded=(p_idx == 0)):
                n = len(proj.subtasks)
                done = sum(1 for t in proj.subtasks if t["done"])
                st.progress(proj.progress(), text=f"{done} of {n} steps done" if n else "no steps yet")

                for s_idx, sub in enumerate(proj.subtasks):
                    with st.container(key=f"row_sub_{p_idx}_{s_idx}"):
                        sc1, sc2 = st.columns([0.84, 0.16], vertical_alignment="center")
                        sub_done = sc1.checkbox(sub["name"], value=sub["done"],
                                                key=f"sub_{p_idx}_{s_idx}")
                        if sub_done != sub["done"]:
                            proj.toggle_subtask(s_idx)
                            pm.save()                  # sub-task changes don't save by themselves
                            st.rerun()
                        if sc2.button("✕", key=f"del_sub_{p_idx}_{s_idx}", help="Delete step",
                                      width="stretch"):
                            proj.remove_subtask(s_idx)
                            pm.save()
                            st.rerun()

                with st.form(f"add_sub_{p_idx}", clear_on_submit=True):
                    new_sub = st.text_input("Add a step", label_visibility="collapsed",
                                            placeholder="Add a small step...")
                    if st.form_submit_button("Add step", width="stretch") and new_sub.strip():
                        proj.add_subtask(new_sub.strip())
                        pm.save()
                        st.rerun()

                if st.button("Delete project", key=f"del_proj_{p_idx}", width="stretch"):
                    pm.remove_project(p_idx)
                    st.rerun()


# ================================================================ TAB 3: STUDY TIMER
class SilentSound:
    """The browser version plays no sound from the server."""
    current = None

    def toggle(self, kind):
        return None

    def stop(self):
        pass


if "timer" not in st.session_state:
    # the same StudyTimer class as the desktop app: 50/10 x2 -> 20, 2-hour guard, stats
    st.session_state.timer = stimer.StudyTimer(save_file=STATS_FILE, sound=SilentSound())

MESSAGES = {"study": "Focus time. You've got this!",
            "break": "Time for a small break.",
            "long_break": "Long break time. You deserve it!"}


def show_events(events):
    for kind, value in events:
        if kind == stimer.PHASE_CHANGED:
            st.toast(MESSAGES[value])
        else:                                          # OVERWORK or SET_DONE
            st.toast(value, icon="🎉" if kind == stimer.SET_DONE else "☕")


def on_skip():
    show_events(st.session_state.timer.skip())


@st.fragment(run_every=1)                              # only this part refreshes each second
def timer_panel():
    t = st.session_state.timer
    show_events(t.update())

    st.markdown(f"<p class='meraki-phase'>{t.phase_label()}</p>"
                f"<p class='meraki-session'>{t.session_text()}</p>"
                f"<p class='meraki-clock'>{t.time_text()}</p>", unsafe_allow_html=True)
    st.progress(t.progress())

    with st.container(key="row_timer_buttons"):
        b1, b2, b3 = st.columns(3)
        b1.button("⏸ Pause" if t.running else "▶ Start", on_click=t.toggle,
                  width="stretch", type="primary", key="t_toggle")
        b2.button("↺ Reset", on_click=t.reset, width="stretch", key="t_reset")
        b3.button("⏭ Skip", on_click=on_skip, width="stretch", key="t_skip")

    st.caption(f"📊 {t.studied_text()} · {t.sessions_today} sessions completed")
    if t.finished:
        st.success("You finished the whole pomodoro. Great job!")


with tab3:
    st.subheader("Study Timer")
    st.caption("50 min focus → 10 min break, twice, then a 20 min long break.")
    timer_panel()
