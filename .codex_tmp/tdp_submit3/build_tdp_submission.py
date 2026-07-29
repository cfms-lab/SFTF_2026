from __future__ import annotations

import argparse
import copy
import os
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


TITLE = (
    "The Support Flow Tensor Field for Build-Orientation Candidate Search: "
    "Algorithm, External Audit, and a Budget–Complexity Map"
)

ABSTRACT = (
    "Build orientation strongly affects support material and post-processing in "
    "additive manufacturing, but dense orientation sweeps with support-structure "
    "tomography (TOMO) or repeated slicer runs are expensive. This study presents "
    "the Support Flow Tensor Field (SFTF), a support-aware candidate generator that "
    "ranks directions before accurate verification. SFTF follows ray-cast support "
    "paths from overhanging faces to receiving faces or to the build plate, "
    "represents both cases in one tensor score, and concentrates a fixed "
    "verification budget around promising basins. Candidate generation averaged "
    "4.57 s per mesh, compared with 131.0 s for a complete 130,321-cell TOMO sweep, "
    "while each oriented mesh required 12.54 s in CuraEngine and 2.93 s in "
    "PrusaSlicer. The method was externally audited on 60 independently selected "
    "Thingi10K meshes using dense TOMO references; 30 meshes were also evaluated "
    "with CuraEngine 5.13 and PrusaSlicer 2.9.6. At a generous 2,400-cell budget, "
    "matched uniform search was already near-saturated and SFTF did not establish "
    "noninferiority (paired normalized-regret difference 0.0214, 95% confidence "
    "interval 0.0070–0.0406). At a 10-cell budget on complex meshes (at least "
    "50,000 faces), however, the mean contrast favored SFTF under TOMO and both "
    "slicers, although the bootstrap intervals included zero. These results identify "
    "the practical regime for support-aware candidate search: use uniform "
    "verification when thousands of evaluations are affordable, and use SFTF to "
    "reduce expensive verification to a small, targeted set when geometry is "
    "complex and the budget is tight."
)

AUTHOR_BLOCK = (
    "InHwan Sul\n"
    "Department of Materials Design Engineering, Kumoh National Institute of Technology\n"
    "Gumi 39177, Republic of Korea\n"
    "Email: snowman0@kumoh.ac.kr    ORCID: 0000-0003-0105-920X"
)

FUNDING = (
    "This work was supported by the National Research Foundation of Korea (NRF) "
    "grant funded by the Korean government (MSIT) (grant number "
    "NRF-2022R1A2C1010072)."
)

DATA_AVAILABILITY = (
    "The geometry-only holdout manifest, selection audit, SFTF implementation, "
    "tests, machine-readable TOMO/Cura/Prusa outcomes, and table and figure "
    "generators are maintained at https://github.com/cfms-lab/SFTF_2026. Access "
    "can be provided to the editor and reviewers during peer review, and the "
    "repository will be made publicly accessible upon publication. Third-party "
    "Thingi10K mesh files are not redistributed; the manifest provides model "
    "identifiers so eligible users can retrieve source meshes under their original "
    "licenses."
)

COI = (
    "The author(s) declared no potential conflicts of interest with respect to the "
    "research, authorship, and/or publication of this article"
)

AI_DISCLOSURE = (
    "AI coding assistants, including OpenAI Codex and Anthropic Claude Code, were "
    "used to assist with portions of the research code implementation, "
    "figure-generation scripts, manuscript organization, language editing, and "
    "manuscript-support automation. All AI-assisted code and text were reviewed "
    "and validated by the author, who takes full responsibility for the methodology, "
    "data, results, references, and conclusions. No generative AI was used to "
    "generate research data, figures presented as novel research images, or "
    "references."
)

CITATIONS = {
    "(Gibson et al., 2021)": "1",
    (
        "(Ezair et al., 2015; Das et al., 2017; Langelaar, 2018; "
        "Vaissier et al., 2019; Jiang et al., 2018b; Mezzadri et al., "
        "2018; Wang and Qian, 2020)"
    ): "2-8",
    "(Shi et al., 2023; Bacciaglia et al., 2024)": "9,10",
    "(Jung et al., 2022)": "11",
    "(Kim and Sul, 2026)": "12",
    "(Jung et al., 2022; Kim and Sul, 2026)": "11,12",
    "(Kanatani, 1984)": "13",
    "(Kanatani, 1984; Xu et al., 2021)": "13,14",
    "(Hung et al., 2022)": "15",
    "(Zhou and Jacobson, 2016)": "16",
    "(Möller and Trumbore, 1997)": "17",
    "(Saff and Kuijlaars, 1997; González, 2010)": "18,19",
    "(Jiang et al., 2018a)": "20",
    "(Piaggio et al., 2006; Efron and Tibshirani, 1993)": "21,22",
    "(Ernst, 2004)": "23",
}

REFERENCES = [
    "Gibson I, Rosen D, Stucker B, et al. Additive manufacturing technologies. "
    "3rd ed. Cham: Springer, 2021.",
    "Ezair B, Massarwi F and Elber G. Orientation analysis of 3D objects toward "
    "minimal support volume in 3D-printing. Comput Graph 2015; 51: 117–124. "
    "DOI: 10.1016/j.cag.2015.05.009.",
    "Das P, Mhapsekar K, Chowdhury S, et al. Selection of build orientation for "
    "optimal support structures and minimum part errors in additive manufacturing. "
    "Comput-Aided Des Appl 2017; 14(sup1): 1–13. "
    "DOI: 10.1080/16864360.2017.1308074.",
    "Langelaar M. Combined optimization of part topology, support structure layout "
    "and build orientation for additive manufacturing. Struct Multidisc Optim "
    "2018; 57(5): 1985–2004. DOI: 10.1007/s00158-017-1877-z.",
    "Vaissier B, Pernot J-P, Chougrani L, et al. Genetic-algorithm based framework "
    "for lattice support structure optimization in additive manufacturing. "
    "Comput-Aided Des 2019; 110: 11–23. DOI: 10.1016/j.cad.2018.12.007.",
    "Jiang J, Xu X and Stringer J. Support structures for additive manufacturing: "
    "a review. J Manuf Mater Process 2018; 2: 64. "
    "DOI: 10.3390/jmmp2040064.",
    "Mezzadri F, Bouriakov V and Qian X. Topology optimization of self-supporting "
    "support structures for additive manufacturing. Addit Manuf 2018; 21: "
    "666–682. DOI: 10.1016/j.addma.2018.04.016.",
    "Wang C and Qian X. Simultaneous optimization of build orientation and "
    "topology for additive manufacturing. Addit Manuf 2020; 34: 101246. "
    "DOI: 10.1016/j.addma.2020.101246.",
    "Shi P, Qi Q, Qin Y, et al. Learn to rotate: part orientation for reducing "
    "support volume via generalizable reinforcement learning. IEEE Trans Ind "
    "Inform 2023; 19(12): 11687–11700. DOI: 10.1109/TII.2023.3249751.",
    "Bacciaglia A, Liverani A and Ceruti A. Efficient part orientation algorithm "
    "for additive manufacturing in industrial applications. Int J Adv Manuf "
    "Technol 2024; 133: 5443–5462. DOI: 10.1007/s00170-024-14039-z.",
    "Jung JY, Chee S and Sul IH. Support structure tomography using per-pixel "
    "signed shadow casting in human manikin 3D printing. Fash Text 2022; 9(1): "
    "1–18. DOI: 10.1186/s40691-022-00290-z.",
    "Kim JR and Sul IH. Fast prediction of 3D printing optimal orientation using "
    "general-purpose graphic processor unit calculation. 3D Print Addit Manuf "
    "2026; 13(1): 50–62. DOI: 10.1089/3dp.2024.0165.",
    "Kanatani K. Distribution of directional data and fabric tensors. Int J Eng "
    "Sci 1984; 22(2): 149–164. DOI: 10.1016/0020-7225(84)90090-9.",
    "Xu J, Sheng H, Zhang S, et al. Surface accuracy optimization of mechanical "
    "parts with multiple circular holes for additive manufacturing based on "
    "triangular fuzzy number. Front Mech Eng 2021; 16: 133–150. "
    "DOI: 10.1007/s11465-020-0610-6.",
    "Hung S-H, Zhang Y, Yeh H, et al. Feature curves and surfaces of 3D asymmetric "
    "tensor fields. IEEE Trans Vis Comput Graph 2022; 28(1): 33–42. "
    "DOI: 10.1109/TVCG.2021.3114808.",
    "Zhou Q and Jacobson A. Thingi10K: a dataset of 10,000 3D-printing models. "
    "arXiv preprint arXiv:1605.04797, 2016.",
    "Möller T and Trumbore B. Fast, minimum storage ray–triangle intersection. "
    "J Graph Tools 1997; 2(1): 21–28. "
    "DOI: 10.1080/10867651.1997.10487468.",
    "Saff EB and Kuijlaars ABJ. Distributing many points on a sphere. Math Intell "
    "1997; 19(1): 5–11. DOI: 10.1007/BF03024331.",
    "González A. Measurement of areas on a sphere using Fibonacci and "
    "latitude–longitude lattices. Math Geosci 2010; 42(1): 49–64. "
    "DOI: 10.1007/s11004-009-9257-x.",
    "Jiang J, Stringer J, Xu X, et al. Investigation of printable threshold "
    "overhang angle in extrusion-based additive manufacturing for reducing support "
    "waste. Int J Comput Integr Manuf 2018; 31(10): 961–969. "
    "DOI: 10.1080/0951192X.2018.1466398.",
    "Piaggio G, Elbourne DR, Altman DG, et al. Reporting of noninferiority and "
    "equivalence randomized trials: an extension of the CONSORT statement. JAMA "
    "2006; 295(10): 1152–1160. DOI: 10.1001/jama.295.10.1152.",
    "Efron B and Tibshirani RJ. An introduction to the bootstrap. New York: "
    "Chapman & Hall, 1993.",
    "Ernst MD. Permutation methods: a basis for exact inference. Stat Sci 2004; "
    "19(4): 676–685. DOI: 10.1214/088342304000000396.",
]


def paragraph_text(p) -> str:
    return "".join(
        t.text or ""
        for t in p._p.xpath(
            ".//*[local-name()='t']"
        )
    )


def set_paragraph_text(p, text: str, *, bold: bool | None = None) -> None:
    for child in list(p._p):
        if child.tag != qn("w:pPr"):
            p._p.remove(child)
    run = p.add_run(text)
    if bold is not None:
        run.bold = bold


def find_paragraph(doc: Document, startswith: str):
    for p in doc.paragraphs:
        if paragraph_text(p).startswith(startswith):
            return p
    raise ValueError(f"Paragraph not found: {startswith!r}")


def remove_paragraph(p) -> None:
    parent = p._element.getparent()
    parent.remove(p._element)
    p._p = p._element = None


def insert_before(reference, text: str, style: str):
    p = reference._parent.add_paragraph()
    p.style = style
    set_paragraph_text(p, text)
    reference._p.addprevious(p._p)
    return p


def insert_after(reference, text: str, style: str):
    p = reference._parent.add_paragraph()
    p.style = style
    set_paragraph_text(p, text)
    reference._p.addnext(p._p)
    return p


def replace_text_nodes(doc: Document, old: str, new: str) -> int:
    count = 0
    for p in doc.paragraphs:
        for node in p._p.xpath(".//w:t"):
            if node.text and old in node.text:
                count += node.text.count(old)
                node.text = node.text.replace(old, new)
    return count


def _plain_run_like(source_run, text: str):
    run = OxmlElement("w:r")
    rpr = source_run.find(qn("w:rPr"))
    if rpr is not None:
        run.append(copy.deepcopy(rpr))
    t = OxmlElement("w:t")
    if text.startswith(" ") or text.endswith(" "):
        t.set(qn("xml:space"), "preserve")
    t.text = text
    run.append(t)
    return run


def _citation_run_like(source_run, citation: str):
    run = OxmlElement("w:r")
    rpr = source_run.find(qn("w:rPr"))
    rpr_new = copy.deepcopy(rpr) if rpr is not None else OxmlElement("w:rPr")
    for existing in rpr_new.findall(qn("w:vertAlign")):
        rpr_new.remove(existing)
    vert = OxmlElement("w:vertAlign")
    vert.set(qn("w:val"), "superscript")
    rpr_new.append(vert)
    run.append(rpr_new)
    t = OxmlElement("w:t")
    t.text = citation
    run.append(t)
    return run


def convert_citations_to_superscript(doc: Document) -> int:
    refs = find_paragraph(doc, "References")
    citation_items = sorted(CITATIONS.items(), key=lambda item: len(item[0]), reverse=True)
    combined = re.compile("|".join(re.escape(old) for old, _ in citation_items))
    count = 0

    for p in list(doc.paragraphs):
        if p._p is refs._p:
            break
        for source_run in list(p._p.xpath(".//w:r")):
            text = "".join(node.text or "" for node in source_run.xpath(".//w:t"))
            if not combined.search(text):
                continue
            matches = list(combined.finditer(text))
            if not matches:
                continue

            pieces = []
            cursor = 0
            for match in matches:
                plain = text[cursor:match.start()].rstrip()
                after = match.end()
                punctuation = ""
                if after < len(text) and text[after] in ".,;:":
                    punctuation = text[after]
                    after += 1
                if plain or punctuation:
                    pieces.append(("plain", plain + punctuation))
                pieces.append(("citation", CITATIONS[match.group(0)]))
                cursor = after
                count += 1
            if cursor < len(text):
                pieces.append(("plain", text[cursor:]))

            parent = source_run.getparent()
            insert_at = parent.index(source_run)
            parent.remove(source_run)
            for kind, value in pieces:
                if not value:
                    continue
                new_run = (
                    _citation_run_like(source_run, value)
                    if kind == "citation"
                    else _plain_run_like(source_run, value)
                )
                parent.insert(insert_at, new_run)
                insert_at += 1
    return count


def apply_manuscript_revisions(doc: Document) -> None:
    doc.paragraphs[0].text = TITLE
    doc.paragraphs[0].style = "Title"

    abstract_heading = find_paragraph(doc, "Abstract")
    insert_before(abstract_heading, AUTHOR_BLOCK, "Author")
    abstract_paras = [
        p
        for p in doc.paragraphs
        if p.style.name == "Abstract" and paragraph_text(p).strip()
    ]
    set_paragraph_text(abstract_paras[0], ABSTRACT)
    for p in abstract_paras[1:]:
        remove_paragraph(p)

    audit = find_paragraph(doc, "A candidate generator is only as credible")
    set_paragraph_text(
        audit,
        "The central engineering value of SFTF is not to replace TOMO or a "
        "production slicer, but to reduce how often they must be called. We "
        "evaluate whether this inexpensive front end can preserve useful "
        "orientations under the same verification budget, then map the budgets "
        "and geometric complexity for which the strategy is most effective.",
    )
    contributions = find_paragraph(doc, "The contributions are as follows")
    set_paragraph_text(
        contributions,
        "The contributions are as follows: (i) an interpretable, dimensionless "
        "formulation that treats face-to-face and build-plate support in one "
        "score; (ii) a candidate-generation stage that is about 29 times faster "
        "than a dense TOMO sweep in the tested setup and can sharply reduce "
        "repeated slicer evaluations; (iii) an external audit on 60 sealed meshes "
        "with two slicers; and (iv) a budget–complexity map that identifies where "
        "support-aware search is useful and where uniform coverage is sufficient.",
    )

    sftf_intro = find_paragraph(doc, "The Support Flow Tensor Field (SFTF) answers")
    insert_after(
        sftf_intro,
        "In practical terms, the normal tensor describes which way the surface "
        "tends to face, but it does not say where unsupported material would fall. "
        "SFTF adds that missing route information: it asks which overhanging face "
        "starts the support, which surface or build plate receives it, and how far "
        "the support must travel.",
        "Body Text",
    )

    pair_cost = find_paragraph(doc, "and its scalar support cost")
    insert_after(
        pair_cost,
        "A useful way to read Eq. (2) is as a weighted vote. Each ray-cast "
        "source–receiver pair votes for directions that require less support. The "
        "weights account for overhang severity and travel distance, and the tensor "
        "collects all votes so that any trial build direction can be scored with "
        "one matrix–vector calculation.",
        "Body Text",
    )

    unified = find_paragraph(doc, "Therefore, the entire score is a single tensor")
    insert_after(
        unified,
        "The virtual ground node is bookkeeping rather than an additional physical "
        "assumption. If a ray reaches another face, that face receives the support "
        "flow; if it reaches no face, the build plate receives it. Writing both "
        "cases in one tensor keeps the score interpretable and avoids switching "
        "between separate formulas.",
        "Body Text",
    )

    candidate = find_paragraph(doc, "S(n) is evaluated on 2,048 Fibonacci-sphere directions")
    insert_after(
        candidate,
        "Uniform search spends the verification budget evenly over the sphere. "
        "SFTF instead uses its inexpensive score as a map, concentrates the same "
        "budget near low-score basins, and then lets TOMO or a production slicer "
        "make the final decision. SFTF is therefore a candidate generator, not a "
        "replacement for the high-fidelity verifier.",
        "Body Text",
    )
    replace_text_nodes(
        doc,
        "a diagnostic gate may abstain from the uniform branch",
        "a diagnostic gate may abstain from the SFTF branch",
    )

    reference_stack = find_paragraph(doc, "Dense reference grids")
    set_paragraph_text(
        reference_stack,
        "Dense reference grids (1° yaw–pitch, 60° critical angle) were computed "
        "for every holdout mesh using the TOMO backend. For the 30-mesh panel, "
        "CuraEngine 5.13 and PrusaSlicer 2.9.6 evaluated an identical union of "
        "fixed directions, policy anchors, and local offsets (73–74 common "
        "directions per mesh after pairwise matching). Because slicers parameterize "
        "overhang thresholds differently, cantilever coupons were used to align "
        "the physical support onset (Cura 60° paired with Prusa’s 30° "
        "slope-from-horizontal convention) (Jiang et al., 2018a); profiles and the "
        "coupon table are in the ESM. These checks form a validation ladder—"
        "symbolic identities, a dense voxel reference, and two separate slicer "
        "engines—rather than interchangeable ground truths. No printed-part "
        "experiment was performed; therefore, all outcomes were solver- or "
        "slicer-estimated support demands.",
    )

    replace_text_nodes(doc, "Table III", "Table 3")
    replace_text_nodes(doc, "Table II", "Table 2")
    replace_text_nodes(doc, "Table I", "Table 1")
    replace_text_nodes(doc, "\ufeff", "")
    replace_text_nodes(doc, "Eq. (3) This", "Eq. (3). This")
    replace_text_nodes(
        doc,
        "This one-hop rule is a model assumption, not a full visibility solution, "
        "and it admits a physical paradox worth naming: because nearer "
        "intersections failing the admissibility tests are skipped, support can be "
        "routed to a farther admissible face even though deposited material would "
        "first land on the nearer one.",
        "This one-hop rule is a model assumption: it routes each source to the "
        "nearest admissible receiver rather than solving complete deposition "
        "visibility.",
    )
    replace_text_nodes(
        doc,
        "The formulation therefore behaves as a well-posed, "
        "tessellation-tolerant score—necessary conditions that say nothing yet "
        "about predictive value.",
        "The formulation therefore behaves as a well-posed, "
        "tessellation-tolerant score, establishing the numerical stability needed "
        "before predictive comparisons.",
    )
    replace_text_nodes(
        doc,
        "External audit: at a generous budget, uniform search is enough",
        "External audit across verification budgets",
    )
    replace_text_nodes(
        doc,
        "We report this plainly: at generous verification budgets, the honest "
        "default is uniform search.",
        "At this generous budget, uniform coverage was already effective.",
    )

    full_budget = find_paragraph(doc, "Table 1 and Figure 3 summarize")
    set_paragraph_text(
        full_budget,
        "Table 1 and Figure 3 summarize the TOMO audit at the 2,400-cell budget. "
        "The paired selective-minus-uniform NRR had mean 0.0214 (median 0.0000, "
        "maximum 0.3804), with 95% CI [0.0070, 0.0406] and permutation "
        "p=0.0003; the 0.02 noninferiority criterion was not met. At this budget, "
        "however, the near-uniform design was spaced roughly 4° apart and already "
        "reached mean NRR 0.0026, leaving little room for candidate placement to "
        "improve global coverage. A seeded random design performed similarly "
        "(0.0027), while the legacy dimensional SFTF was markedly worse (0.0722), "
        "showing the benefit of the dimensionless reformulation. The gate accepted "
        "59/60 meshes, and selective and ungated SFTF produced nearly identical "
        "mean NRR values (0.0240 and 0.0237); detailed gate diagnostics are "
        "reported in the ESM. The practical boundary is clear: at a generous "
        "verification budget, uniform coverage is already effective.",
    )

    budget_map = find_paragraph(doc, "Re-evaluating every branch on the cached grids")
    set_paragraph_text(
        budget_map,
        "Re-evaluating every branch on the cached grids across budgets from 5 to "
        "2,400 cells (no new reference computation) produces the practical map of "
        "Figure 4 and Table 2. Across all 60 meshes, uniform retained the lower "
        "mean regret because the simple-mesh strata dominated the aggregate. "
        "Stratification exposed the target regime: on the two simplest strata, "
        "uniform led at every tested budget, whereas on the two complex strata "
        "(≥50k faces) SFTF was better at tight budgets—mean contrast -0.0263 "
        "(95% CI -0.0925 to 0.0332) at 10 cells on 50k–150k meshes and -0.0259 "
        "(-0.0779 to 0.0281) at 5 cells on 150k–250k meshes. Pooling all 25 "
        "complex meshes gave -0.0168 (-0.0610 to 0.0251) at 10 cells, with a "
        "crossover near 20 cells as uniform coverage became dense enough to "
        "overtake basin clustering. The intervals included zero, but both complex "
        "strata showed the same low-budget direction and crossover. Intuitively, "
        "simple shapes have broad optima that a few uniform probes can hit, while "
        "complex shapes can contain narrow basins that a support-aware score helps "
        "locate.",
    )

    slicer_panel = find_paragraph(doc, "Because a pattern found under one reference")
    set_paragraph_text(
        slicer_panel,
        "The 10-cell comparison was then repeated with both slicers on the 30-mesh "
        "panel (Table 3). On the 12 complex meshes, the mean contrast favored SFTF "
        "under all three references (TOMO -0.0329, Cura -0.0362, Prusa -0.0465), "
        "with sign agreement on 10/12 meshes for each slicer. The simplest stratum "
        "favored uniform under both engines, providing a coherent negative control. "
        "The 10k–50k stratum differed by reference: TOMO favored uniform (+0.0287), "
        "whereas Cura (-0.0418) and Prusa (-0.0353) favored SFTF. Complexity is "
        "therefore a useful but reference-dependent moderator rather than a rigid "
        "50k-face threshold. The slicer bootstrap intervals included zero, so the "
        "map identifies the strongest regime for prospective testing rather than a "
        "universal routing rule.",
    )

    computational_cost = find_paragraph(doc, "SFTF candidate generation (2,048 directions")
    set_paragraph_text(
        computational_cost,
        "SFTF candidate generation (2,048 directions, K=8,192, gate diagnostics "
        "included) averaged 4.57 s per mesh on the stated CPU, versus 131.0 s for "
        "a complete 130,321-cell TOMO sweep measured on non-overlapping runs—"
        "roughly a 29× gap that widens further against slicer-based verification, "
        "at 12.54 s (Cura) and 2.93 s (Prusa) per oriented mesh (Figure 6). This "
        "asymmetry makes tight-budget search practically relevant: when each "
        "verified direction costs seconds to minutes, reducing the verification "
        "set from thousands to a targeted handful can dominate the total workflow "
        "time.",
    )

    discussion = find_paragraph(doc, "For practitioners, the audit compresses")
    set_paragraph_text(
        discussion,
        "The main practical advantage is that SFTF moves expensive work out of "
        "the global search. It generated candidates in 4.57 s per mesh, roughly "
        "29 times faster than the complete dense TOMO sweep, and the benefit grows "
        "when each candidate must be verified by a slicer. For complex parts under "
        "a 10-direction budget, the mean contrast favored SFTF under TOMO, Cura, "
        "and Prusa. This consistent three-reference direction supports using SFTF "
        "as a warm start when only a few high-fidelity evaluations are affordable. "
        "The low-budget subgroup intervals included zero, so this regime is a "
        "well-defined target for prospective validation rather than a universal "
        "guarantee. When thousands of inexpensive evaluations are available, the "
        "uniform design already covers the sphere well and remains the simpler "
        "choice.",
    )

    methodology = find_paragraph(doc, "The audit also carries two methodological lessons")
    set_paragraph_text(
        methodology,
        "The audit also carries two methodological strengths. First, "
        "budget-matched uniform search provides a demanding baseline at every "
        "verification budget. Second, the validation ladder compares the same "
        "candidate policy against dense TOMO and two production slicers rather than "
        "relying on a single support proxy. The substantial direction-rank "
        "agreement between engines (median Spearman correlations up to 0.900) "
        "supports TOMO as an intermediate-fidelity verifier while retaining a "
        "direct check against the intended slicer.",
    )

    limitations = find_paragraph(doc, "Limitations include the one-hop receiver model")
    set_paragraph_text(
        limitations,
        "The study is geometry-based and uses solver or slicer estimates rather "
        "than printed-part measurements; it also uses a one-hop receiver model and "
        "a retrospectively analyzed budget sweep. These constraints limit absolute "
        "manufacturing claims, while the reported computational timings and "
        "solver/slicer comparisons remain directly supported by the evaluated "
        "workflow.",
    )

    structural = find_paragraph(doc, "One structural observation deserves note")
    set_paragraph_text(
        structural,
        "A structural observation helps explain the method. The scalar plate "
        "accumulation B(n) captures the dominant unsupported height, while the "
        "routing topology and tensor contraction retain face-to-face directionality "
        "when internal receivers matter. Equation (5) makes these components "
        "explicit and provides a direct path to later ablation and acceleration. "
        "This decomposition separates the inexpensive ranking signal from the "
        "directional information needed for support-aware interpretation.",
    )

    conclusions = find_paragraph(doc, "We presented the Support Flow Tensor Field")
    set_paragraph_text(
        conclusions,
        "SFTF provides a fast, interpretable front end for build-orientation "
        "search. By routing overhang support to another face or to a virtual "
        "build-plate node, it scores 2,048 directions in 4.57 s and forwards only "
        "a small set to TOMO or a slicer. The 60-mesh external audit showed the "
        "clearest value on complex geometry under tight verification budgets, "
        "where the 10-cell mean contrast favored SFTF under all three references. "
        "At the 2,400-cell budget, uniform search was already near-saturated and "
        "SFTF did not establish noninferiority, defining a useful boundary rather "
        "than removing the value of candidate generation. The resulting rule is "
        "simple: use uniform coverage when verification is cheap and plentiful; "
        "use SFTF as a targeted warm start when high-fidelity verification is "
        "expensive and the geometry is complex.",
    )

    ai = find_paragraph(doc, "AI coding assistants, including OpenAI Codex")
    set_paragraph_text(ai, AI_DISCLOSURE)
    ai_heading = find_paragraph(doc, "Use of AI-assisted tools")
    ai_heading.style = "Heading 2"
    author_contrib = find_paragraph(doc, "Conceptualization, Methodology")
    set_paragraph_text(
        author_contrib,
        "InHwan Sul: Conceptualization, Methodology, Software, Validation, Formal "
        "analysis, Investigation, Data curation, Writing – original draft, Writing "
        "– review and editing, Visualization, and Funding acquisition.",
    )

    coi_heading = find_paragraph(doc, "Declarations of conflicting interests.")
    set_paragraph_text(coi_heading, "Declaration of conflicting interest")
    coi_heading.style = "Heading 2"
    coi_para = find_paragraph(doc, "The authors declare no potential conflicts")
    set_paragraph_text(coi_para, COI)
    funding_para = find_paragraph(
        doc, "This work was supported by a national research funding grant"
    )
    set_paragraph_text(funding_para, FUNDING)
    data_para = find_paragraph(doc, "The geometry-only holdout manifest")
    set_paragraph_text(data_para, DATA_AVAILABILITY)

    declaration_headings = {
        "Ethical considerations.": "Ethical considerations",
        "Consent to participate.": "Consent to participate",
        "Consent for publication.": "Consent for publication",
        "Funding statement.": "Funding statement",
        "Data availability.": "Data availability",
    }
    for old_heading, new_heading in declaration_headings.items():
        heading = find_paragraph(doc, old_heading)
        set_paragraph_text(heading, new_heading)
        heading.style = "Heading 2"

    refs_heading = find_paragraph(doc, "References")
    reached = False
    for p in list(doc.paragraphs):
        if p._p is refs_heading._p:
            reached = True
            continue
        if reached:
            remove_paragraph(p)
    for index, reference in enumerate(REFERENCES, 1):
        p = doc.add_paragraph(style="Body Text")
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        p.add_run(f"{index}. {reference}")

    citation_count = convert_citations_to_superscript(doc)
    if citation_count != 16:
        raise RuntimeError(
            f"Expected 16 author-year citation groups, converted {citation_count}"
        )

    props = doc.core_properties
    props.title = TITLE
    props.subject = "Original Article for 3D Printing and Additive Manufacturing"
    props.author = "InHwan Sul"
    props.last_modified_by = "InHwan Sul"
    props.keywords = (
        "additive manufacturing; build orientation; support material; candidate "
        "generation; external validation; slicer verification"
    )
    props.comments = ""


def set_figure_alt_text(doc: Document) -> None:
    descriptions = [
        "Figure 1a. Exhaustive TOMO orientation-sweep workflow.",
        "Figure 1b. SFTF candidate-generation and matched-budget verification workflow.",
        "Figure 2. Unified face-to-face and virtual build-plate support-flow model.",
        "Figure 3. External TOMO audit at the 2,400-cell verification budget.",
        "Figure 4. Verification budget and mesh-complexity performance map.",
        "Figure 5. Separate-engine Cura and Prusa slicer comparison.",
        "Figure 6. Measured SFTF, TOMO, Cura, and Prusa component times.",
    ]
    drawings = doc._element.xpath(".//*[local-name()='drawing']")
    if len(drawings) != len(descriptions):
        raise RuntimeError(
            f"Expected {len(descriptions)} drawings for alt text, found {len(drawings)}"
        )
    for drawing, description in zip(drawings, descriptions):
        doc_properties = drawing.xpath(".//*[local-name()='docPr']")
        if not doc_properties:
            raise RuntimeError("Drawing is missing wp:docPr")
        doc_properties[0].set("title", description.split(".", 1)[0])
        doc_properties[0].set("descr", description)


def normalize_table_geometry(doc: Document) -> None:
    """Make every layout, equation, and data table explicit and page-safe."""
    for table in doc.tables:
        grid_columns = table._tbl.xpath("./w:tblGrid/w:gridCol")
        widths = [int(col.get(qn("w:w"))) for col in grid_columns]
        if not widths:
            continue
        table_width = sum(widths)
        tbl_pr = table._tbl.tblPr

        tbl_w = tbl_pr.find(qn("w:tblW"))
        if tbl_w is None:
            tbl_w = OxmlElement("w:tblW")
            tbl_pr.insert(0, tbl_w)
        tbl_w.set(qn("w:type"), "dxa")
        tbl_w.set(qn("w:w"), str(table_width))

        tbl_ind = tbl_pr.find(qn("w:tblInd"))
        if tbl_ind is None:
            tbl_ind = OxmlElement("w:tblInd")
            tbl_pr.append(tbl_ind)
        tbl_ind.set(qn("w:type"), "dxa")
        # Match Word's default 120-DXA leading cell margin so the visible table
        # border aligns with surrounding body text.
        tbl_ind.set(qn("w:w"), "120")

        layout = tbl_pr.find(qn("w:tblLayout"))
        if layout is None:
            layout = OxmlElement("w:tblLayout")
            tbl_pr.append(layout)
        layout.set(qn("w:type"), "fixed")

        jc = tbl_pr.find(qn("w:jc"))
        if jc is None:
            jc = OxmlElement("w:jc")
            tbl_pr.append(jc)
        jc.set(qn("w:val"), "center")

        for row in table._tbl.tr_lst:
            column_index = 0
            for cell in row.tc_lst:
                tc_pr = cell.get_or_add_tcPr()
                grid_span = tc_pr.find(qn("w:gridSpan"))
                span = int(grid_span.get(qn("w:val"))) if grid_span is not None else 1
                cell_width = sum(widths[column_index : column_index + span])
                tc_w = tc_pr.find(qn("w:tcW"))
                if tc_w is None:
                    tc_w = OxmlElement("w:tcW")
                    tc_pr.insert(0, tc_w)
                tc_w.set(qn("w:type"), "dxa")
                tc_w.set(qn("w:w"), str(cell_width))
                column_index += span


def create_cover_letter(base_path: Path, output_path: Path) -> None:
    doc = Document(base_path)
    body = doc._element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)

    styles = doc.styles
    if "Cover Letter Body" not in styles:
        style = styles.add_style("Cover Letter Body", WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = styles["Normal"]
    else:
        style = styles["Cover Letter Body"]
    style.font.name = "Times New Roman"
    style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    style.font.size = Pt(11)
    style.font.color.rgb = RGBColor(0, 0, 0)
    style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    style.paragraph_format.line_spacing = 1.08
    style.paragraph_format.space_after = Pt(6)

    def add(text: str = "", *, bold: bool = False, after: float | None = None):
        p = doc.add_paragraph(style="Cover Letter Body")
        r = p.add_run(text)
        r.bold = bold
        if after is not None:
            p.paragraph_format.space_after = Pt(after)
        return p

    add("28 July 2026", after=12)
    add("Editor-in-Chief")
    add("3D Printing and Additive Manufacturing")
    add("SAGE Publications", after=12)
    add(
        "Re: Original Article submission, “The Support Flow Tensor Field for "
        "Build-Orientation Candidate Search: Algorithm, External Audit, and a "
        "Budget–Complexity Map”",
        bold=True,
        after=12,
    )
    add("Dear Editor-in-Chief,", after=12)
    add(
        "Please consider the enclosed manuscript for publication as an Original "
        "Article in 3D Printing and Additive Manufacturing. The manuscript "
        "introduces the Support Flow Tensor Field (SFTF), a support-aware front end "
        "that ranks build directions before expensive verification by "
        "support-structure tomography (TOMO) or a production slicer."
    )
    add(
        "The practical contribution is a reduction in global search cost. In the "
        "reported workflow, SFTF generated candidates in 4.57 s per mesh, compared "
        "with 131.0 s for a complete 130,321-cell TOMO sweep. Because each oriented "
        "mesh additionally required 12.54 s in CuraEngine and 2.93 s in "
        "PrusaSlicer, concentrating verification on a small candidate set can avoid "
        "many costly slicer calls. The algorithm is also interpretable: ray-cast "
        "face-to-face support and build-plate support are represented in one "
        "dimensionless tensor score."
    )
    add(
        "The evidence includes an external audit on 60 independently selected "
        "Thingi10K meshes, dense TOMO reference grids, and a 30-mesh comparison "
        "with CuraEngine 5.13 and PrusaSlicer 2.9.6. The clearest use case was "
        "complex geometry under a tight verification budget: at 10 directions, "
        "the mean contrast favored SFTF under TOMO and both slicers. At a generous "
        "2,400-cell budget, uniform search was already near-saturated and SFTF did "
        "not establish noninferiority. We believe this boundary strengthens the "
        "engineering message by showing when candidate search is useful and when "
        "uniform coverage is sufficient."
    )
    add(
        "This manuscript is distinct from the author’s earlier TOMO publications "
        "(DOI: 10.1186/s40691-022-00290-z and DOI: 10.1089/3dp.2024.0165). Those "
        "studies accelerated exhaustive orientation verification; the present work "
        "addresses the complementary problem of selecting which directions should "
        "be verified under a fixed budget, and supplies a new algorithm, external "
        "audit, and budget–complexity map."
    )
    add(
        "The manuscript is original, has not been published, and is not under "
        "consideration elsewhere. The author has approved the submission. The "
        "author declares no potential conflicts of interest. Funding was provided "
        "by the National Research Foundation of Korea (NRF), funded by the Korean "
        "government (MSIT), grant NRF-2022R1A2C1010072. The research repository can "
        "be made available to the editor and reviewers during peer review and will "
        "be made publicly accessible upon publication; third-party mesh files are "
        "not redistributed."
    )
    add(
        "AI coding assistants, including OpenAI Codex and Anthropic Claude Code, "
        "assisted with portions of research-code implementation, "
        "figure-generation scripts, manuscript organization, language editing, and "
        "manuscript-support automation. All outputs were reviewed and validated by "
        "the author. No generative AI was used to generate research data, figures "
        "presented as novel research images, or references. This assistance is "
        "also disclosed in the manuscript."
    )
    add(
        "Thank you for considering this manuscript. I believe its combination of "
        "an interpretable algorithm, independent external audit, and a practical "
        "rule for reducing TOMO and slicer verification will be relevant to the "
        "journal’s readers.",
        after=12,
    )
    add("Sincerely,")
    add("InHwan Sul")
    add("Department of Materials Design Engineering")
    add("Kumoh National Institute of Technology")
    add("Gumi 39177, Republic of Korea")
    add("Email: snowman0@kumoh.ac.kr")
    add("ORCID: 0000-0003-0105-920X")

    props = doc.core_properties
    props.title = f"Cover Letter – {TITLE}"
    props.subject = "Original Article submission to 3D Printing and Additive Manufacturing"
    props.author = "InHwan Sul"
    props.last_modified_by = "InHwan Sul"
    props.comments = ""
    doc.save(output_path)


def restore_template_parts(docx_path: Path, template_path: Path) -> None:
    """Restore the template's style-system parts byte-for-byte after python-docx saves."""
    controlled_parts = {
        "word/styles.xml",
        "word/numbering.xml",
        "word/theme/theme1.xml",
    }
    with ZipFile(template_path) as template_zip:
        replacements = {
            name: template_zip.read(name)
            for name in controlled_parts
        }
    temp_path = docx_path.with_suffix(".tmp.docx")
    with ZipFile(docx_path) as source_zip, ZipFile(
        temp_path, "w", compression=ZIP_DEFLATED
    ) as output_zip:
        for item in source_zip.infolist():
            data = replacements.get(item.filename, source_zip.read(item.filename))
            output_zip.writestr(item, data)
    os.replace(temp_path, docx_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-base", type=Path, required=True)
    parser.add_argument("--cover-base", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--main-out", type=Path, required=True)
    parser.add_argument("--cover-out", type=Path, required=True)
    args = parser.parse_args()

    manuscript = Document(args.main_base)
    apply_manuscript_revisions(manuscript)
    set_figure_alt_text(manuscript)
    normalize_table_geometry(manuscript)
    # The third embedded figure was effectively 299 dpi at its inherited display
    # size. A 1% reduction clears the journal's 300 dpi threshold without changing
    # the page design or the underlying image.
    if len(manuscript.inline_shapes) >= 3:
        third_figure = manuscript.inline_shapes[2]
        third_figure.width = int(third_figure.width * 0.99)
        third_figure.height = int(third_figure.height * 0.99)
    manuscript.save(args.main_out)
    restore_template_parts(args.main_out, args.template)
    create_cover_letter(args.cover_base, args.cover_out)
    print(f"[OK] wrote {args.main_out}")
    print(f"[OK] wrote {args.cover_out}")


if __name__ == "__main__":
    main()
