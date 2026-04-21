import heapq
import csv

# ----------------------------
# STATE
# ----------------------------
class State:
    def __init__(self, attendance, missing, score, activity, study_hours, days):
        self.attendance = attendance
        self.missing = missing
        self.score = score
        self.activity = activity
        self.study_hours = study_hours
        self.days = days

    def is_goal(self):
        return self.missing == 0 and self.score >= 70 and self.attendance >= 75


# ----------------------------
# RISK SCORE
# ----------------------------
def risk_score(state):
    return (state.missing * 10 +
            max(0, 70 - state.score) +
            max(0, 75 - state.attendance))


# ----------------------------
# HEURISTIC
# ----------------------------
def heuristic(state):
    return risk_score(state)


# ----------------------------
# ACTIONS
# ----------------------------
def get_neighbors(s):
    neighbors = []

    neighbors.append(("Attend_Class",
        State(s.attendance + 5, s.missing, s.score, s.activity, s.study_hours, s.days - 1), 2))

    neighbors.append(("Study_1_Hour",
        State(s.attendance, s.missing, s.score + 3, s.activity, s.study_hours + 1, s.days - 1), 1))

    if s.missing > 0:
        neighbors.append(("Submit_Assignment",
            State(s.attendance, s.missing - 1, s.score, s.activity, s.study_hours, s.days - 1), 3))

    neighbors.append(("Practice_Quiz",
        State(s.attendance, s.missing, s.score + 5, s.activity, s.study_hours, s.days - 1), 2))

    neighbors.append(("Meet_Tutor",
        State(s.attendance, s.missing, s.score + 8, s.activity, s.study_hours, s.days - 1), 4))

    neighbors.append(("Rest",
        State(s.attendance, s.missing, s.score, s.activity, s.study_hours, s.days - 1), 1))

    return neighbors


# ----------------------------
# A* SEARCH 
# ----------------------------
def a_star(start):
    open_list = []
    visited = set()
    counter = 0  # 🔑 simple tie-breaker

    heapq.heappush(open_list, (0, 0, counter, start, []))

    while open_list:
        f, g, _, current, path = heapq.heappop(open_list)

        key = (current.attendance, current.missing, current.score, current.days)
        if key in visited:
            continue
        visited.add(key)

        if current.is_goal():
            return path, g, current

        for action, nxt, cost in get_neighbors(current):
            counter += 1  # ensure uniqueness

            new_g = g + cost
            new_f = new_g + heuristic(nxt)

            heapq.heappush(
                open_list,
                (new_f, new_g, counter, nxt, path + [action])
            )

    return None, float('inf'), None

def csv_row_to_state(row):
    state = State(
                float(row['attendance_rate']),
                float(row['missing_submissions']),
                float(row['avg_quiz_score']),
                float(row['lms_activity']),
                float(row['study_hours_per_week']),
                float(row['days_to_deadline'])
            )

    return state
# ----------------------------
# READ CSV + RUN
# ----------------------------
def run_from_csv(filename):
    with open(filename, newline='') as file:
        reader = csv.DictReader(file)

        for i, row in enumerate(reader, 1):
            print("\n--- Student", i, "---")

            state = State(
                float(row['attendance_rate']),
                float(row['missing_submissions']),
                float(row['avg_quiz_score']),
                float(row['lms_activity']),
                float(row['study_hours_per_week']),
                float(row['days_to_deadline'])
            )

            print("Initial Risk:", risk_score(state))

            plan, cost, final_state = a_star(state)

            if final_state:
                print("Final Risk:", risk_score(final_state))
                print("Plan:", plan)
                print("Cost:", cost)
            else:
                print("No solution found")


# ----------------------------
# RUN FILE
# ----------------------------
if __name__ == "__main__":
    run_from_csv("STUDEN_1.csv")