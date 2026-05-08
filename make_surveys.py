"""
make_survey.py
==================
Generates a Jisc Online Surveys JSON file for the retrosynthesis expert
evaluation study, based on a template exported from Jisc.

DEPENDENCIES
------------
    pip install cuid2
"""

import json
import copy
import os
from cuid2 import cuid_wrapper

cuid = cuid_wrapper()

# ---------------------------------------------------------------------------
# CONFIGURE YOUR ROUTES HERE
# ---------------------------------------------------------------------------
# Each dict in ROUTES represents one complete synthetic route.
# "steps" is an ordered list of image URLs, one per reaction step.
# Replace every URL below with your actual GitHub raw URLs.

RXN_GIT_PATH = "https://raw.githubusercontent.com/saratanov/multi_expert/main/data/rxns/"
ROUTE_GIT_PATH = "https://raw.githubusercontent.com/saratanov/multi_expert/main/data/routes/"
RXN_PATH = "./data/rxns/"
ROUTE_PATH = "./data/routes/"

MOL_IDS = [3, 5, 25, 26, 35]
SPLITS = ['P', 'F', 'B', 'L', 'M']

ROUTES = {}
for mol_id in MOL_IDS:
    route_num = 1
    mol_routes = []
    for split in SPLITS:
        try:
            rxn_imgs = os.listdir(f"{RXN_PATH}{mol_id}{split}")
            rxns = [RXN_GIT_PATH + img for img in rxn_imgs if img.endswith(".png")]
            route_img = ROUTE_GIT_PATH + f"{mol_id}{split}.png"
            
            mol_routes.append({
                "molecule": f"Molecule {mol_id}",
                "route_num": f"{mol_id}.{route_num}",
                "steps": rxns,
                "route_img": route_img,
            })
            
            route_num += 1
        except:            
            print(f"Warning: No data found for molecule {mol_id} split {split}. Skipping this route.")
    ROUTES[mol_id] = mol_routes
    

# ---------------------------------------------------------------------------
# FIXED ANSWER CHOICES  (copied verbatim from your exported demo)
# ---------------------------------------------------------------------------

STEP_CHOICES = [
    {"value": "Reaction feasible, all good - This is a standard, reliable transformation with extensive literature precedent.", "allowComments": False},
    {"value": "Reaction feasible, unexpected disconnection - The reaction would work but represents nontypical bond disconnection which is inventive and effective, but potentially less precedent.", "allowComments": False},
    {"value": "Non-optimal reagent - The exact reactant may not work in this reaction, but close analogues exist for this transformation with the same bond disconnection.", "allowComments": False},
    {"value": "Unnecessary step - The transformation adds complexity to the synthesis or may not work at all, but is unnecessary for the full route.", "allowComments": False},
    {"value": "Protecting group strategy is wrong / nonoptimal - The protecting group selection is flawed, unnecessary, or inefficient.", "allowComments": False},
    {"value": "Selectivity (regio-,stereo-, chemo-) issues - The reaction would face significant regio-, stereo-, or chemoselectivity challenges.", "allowComments": False},
    {"value": "Functional group compatibility problems - Incompatible functional groups are present in the reactant molecule that would interfere with the desired transformation.", "allowComments": False},
    {"value": "Unlikely disconnection - The proposed transformation is chemically impossible.", "allowComments": False},
    {"value": "Unsure", "allowComments": False},
    {"value": "Other (please specify)", "allowComments": True},
]

OVERALL_FEASIBILITY_CHOICES = [
    {"value": "Excellent — This is a high-quality, practical route I would confidently attempt in the lab", "allowComments": False},
    {"value": "Good — A solid route with minor issues; would likely succeed with standard optimisation", "allowComments": False},
    {"value": "Acceptable — A workable route but with several concerns; significant optimisation needed", "allowComments": False},
    {"value": "Poor — Major feasibility issues; unlikely to succeed without substantial modifications", "allowComments": False},
    {"value": "Not viable — This route contains critical flaws and would not be attempted", "allowComments": False},
]

OVERALL_CONCERNS_CHOICES = [
    {"value": "Poor disconnection strategy — Inefficient or illogical retrosynthetic disconnections", "allowComments": False},
    {"value": "Unnecessarily long route — Route has more steps than necessary to reach the target", "allowComments": False},
    {"value": "Poor convergence — Linear route where a convergent approach would be more efficient", "allowComments": False},
    {"value": "Illogical complexity building — Does not build molecular complexity in a sensible order", "allowComments": False},
    {"value": "Poor protecting group strategy — Inefficient or flawed use of protecting groups", "allowComments": False},
    {"value": "Poor (regio-,stereo-, chemo-) selectivity — High probability of side products", "allowComments": False},
    {"value": "Other (please specify)", "allowComments": True},
]

# ---------------------------------------------------------------------------
# TEMPLATE  (the fixed pages that never change: consent + demographics)
# ---------------------------------------------------------------------------
# Loaded from your exported demo so all metadata, wording, and settings are
# preserved exactly.  Only the route pages are generated fresh.

TEMPLATE_PATH = "template.json"

# ---------------------------------------------------------------------------
# BUILDER FUNCTIONS
# ---------------------------------------------------------------------------

def make_choice_values(choices):
    """Assign fresh integer IDs to a list of choice dicts."""
    import random
    used = set()
    result = []
    for c in choices:
        while True:
            vid = random.randint(10000, 99999)
            if vid not in used:
                used.add(vid)
                break
        result.append({"id": vid, **c})
    return result


def make_note(content: str) -> dict:
    return {
        "id": cuid(),
        "type": "NOTE",
        "content": content,
        "readonly": True,
        "isEditing": False,
    }


def make_choice(title: str, choices: list, required: bool, multicheck: bool,
                question_number: int, plain_text: str) -> dict:
    return {
        "id": cuid(),
        "type": "CHOICE",
        "title": f"<p><span style=\"color:rgb(31, 31, 31)\">{title}</span></p>",
        "values": make_choice_values(choices),
        "readonly": False,
        "isEditing": False,
        "screening": None,
        "isRequired": required,
        "multicheck": multicheck,
        "validation": None,
        "defaultValue": None,
        "questionNumber": question_number,
        "randomiseOptionsOrder": False,
        "titlePlainText": plain_text,
    }


def make_route_page(route: dict, question_counter: list) -> dict:
    """
    Builds a single Jisc page for one complete route.

    question_counter is a one-element list used as a mutable integer so the
    running question number is shared across all route pages.
    """
    mol   = route["molecule"]
    rnum  = route["route_num"]
    steps = route["steps"]
    n     = len(steps)

    questions = []

    # --- Intro note for this route ---
    intro_html = (
        f"<p><span style=\"color:rgb(31, 31, 31)\"><strong>{mol}: Route {rnum}</strong></span></p>"
        f"<p></p>"
        f"<p><span style=\"color:rgb(31, 31, 31)\">Below is a full synthetic route towards {mol}. "
        f"You will now evaluate the {n} reaction step{'s' if n != 1 else ''} individually, "
        f"followed by an assessment of the overall route.</span></p>"
    )
    questions.append(make_note(intro_html))

    # --- One image + one question per step ---
    for i, step_url in enumerate(steps, start=1):
        step_label = f"Reaction {i}"

        # Step image note
        img_html = (
            f"<p><strong>{step_label}</strong></p>"
            f"<p></p>"
            f"<div style=\"display:flex\"><div>"
            f"<img src=\"{step_url}\" width=\"800\" />"
            f"</div></div>"
            f"<p></p>"
        )
        questions.append(make_note(img_html))

        # Step feasibility question
        q_title = f"Reaction {rnum}.{i}: Select the MOST APPROPRIATE category for this reaction"
        questions.append(make_choice(
            title=q_title,
            choices=STEP_CHOICES,
            required=True,
            multicheck=False,
            question_number=question_counter[0],
            plain_text=q_title,
        ))
        question_counter[0] += 1

    # --- Overall route image note ---
    overall_note_html = (
        f"<p><span style=\"color:rgb(31, 31, 31)\"><strong>Overall Route Assessment</strong></span></p>"
        f"<p></p>"
        f"<p><span style=\"color:rgb(31, 31, 31)\">Now please evaluate the complete synthetic route below.</span></p>"
        f"<p></p>"
        f"<div style=\"display:flex;justify-content:flex-start\"><div>"
        f"<img src=\"{route['route_img']}\" width=\"800\" style=\"justify-content:flex-start\" />"
        f"</div></div>"
        f"<p></p>"
    )
    questions.append(make_note(overall_note_html))

    # --- Overall feasibility rating ---
    feas_title = f"Route {rnum}: Considering the complete synthetic route as a whole, please rate the overall synthetic feasibility:"
    questions.append(make_choice(
        title=feas_title,
        choices=OVERALL_FEASIBILITY_CHOICES,
        required=False,
        multicheck=False,
        question_number=question_counter[0],
        plain_text=feas_title,
    ))
    question_counter[0] += 1

    # --- Overall concerns (multi-select) ---
    concerns_title = f"Route {rnum}: Do you have any major concerns about the strategy or practicalities of this route as a whole? Select all that apply:"
    questions.append(make_choice(
        title=concerns_title,
        choices=OVERALL_CONCERNS_CHOICES,
        required=True,
        multicheck=True,
        question_number=question_counter[0],
        plain_text=concerns_title,
    ))
    question_counter[0] += 1

    return {
        "id": cuid(),
        "title": f"{mol} Route {rnum}",
        "isLocked": False,
        "isEditing": False,
        "questions": questions,
        "showTitle": False,
        "description": "",
        "showDescription": False,
        "preventNewQuestions": False,
    }


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def make_survey(mol1, mol2):
    # Load the original exported survey (template pages + all metadata)
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        survey = json.load(f)

    # Keep only the fixed pages (consent page + demographics page = first 2)
    fixed_pages = survey["pages"][:2]

    # Work out where question numbering left off after the fixed pages
    last_fixed_q = max(
        q.get("questionNumber", 0)
        for page in fixed_pages
        for q in page["questions"]
        if "questionNumber" in q
    )
    question_counter = [last_fixed_q + 1]

    # Build one page per route
    print(ROUTES[mol1])
    route_pages = [make_route_page(r, question_counter) for r in ROUTES[mol1]+ROUTES[mol2]]

    survey["pages"] = fixed_pages + route_pages

    out_path = f"surveys/survey_{mol1}_{mol2}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(survey, f, ensure_ascii=False, indent=2)

    print(f"   Survey written to {out_path}")
    print(f"   Fixed pages : {len(fixed_pages)}")
    print(f"   Route pages : {len(route_pages)}")
    print(f"   Total questions (numbered): {question_counter[0] - 1}")
    for r in ROUTES[mol1]+ROUTES[mol2]:
        print(f"   • {r['molecule']} Route {r['route_num']} — {len(r['steps'])} steps")

def main():
    for mol1 in MOL_IDS:
        for mol2 in MOL_IDS:
            if mol1 < mol2:
                print(f"Generating survey for {mol1} and {mol2}...")
                make_survey(mol1, mol2)


if __name__ == "__main__":
    main()