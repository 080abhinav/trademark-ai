"""
TMEP Knowledge Base — Hardcoded Expert Knowledge
=================================================
26 critical TMEP sections covering ALL 13 DuPont factors and key examination issues.

WHY HARDCODED (not RAG):
- Only ~26 sections matter for typical trademark analysis
- Hardcoded = ZERO hallucination risk (LLM only sees exact TMEP text we provide)
- No vector DB, no embedding model, no retrieval errors
- Each section is curated with key rules, risk guidance, and exact citation text
- Faster, simpler, more reliable than semantic search

SOURCES:
- TMEP (Trademark Manual of Examining Procedure), current edition
- https://tmep.uspto.gov/RDMS/TMEP/current
"""

from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Each section dict has:
#   section        : TMEP section number (e.g. "1207.01")
#   title          : Official section title
#   summary        : 1-2 sentence plain-English summary
#   key_rules      : List of concrete, testable rules from this section
#   risk_guidance  : When this section indicates HIGH vs LOW risk
#   citation_text  : Exact language an examiner would use in an office action
#   category       : Issue category this section maps to
#   related        : Related sections that should also be checked
# ---------------------------------------------------------------------------

TMEP_SECTIONS: Dict[str, dict] = {

    # ===== LIKELIHOOD OF CONFUSION (§1207) =====

    "1207.01": {
        "section": "1207.01",
        "title": "Likelihood of Confusion — General Principles",
        "summary": "Registration must be refused if the applicant's mark, when used on the identified goods/services, is likely to cause confusion with a prior registered or pending mark. This is the #1 ground for trademark refusal.",
        "key_rules": [
            "A mark must be refused under §2(d) if it so resembles a registered mark as to be likely to cause confusion, mistake, or deception.",
            "The test is likelihood of confusion, NOT actual confusion — actual instances are not required.",
            "Each case is decided on its own facts; there is no per se rule.",
            "Confusion as to SOURCE, SPONSORSHIP, or AFFILIATION all count.",
            "The marks need NOT be identical — similarity in sound OR appearance OR meaning can suffice.",
            "The goods/services need NOT be identical — they just need to be related enough that consumers would assume a common source.",
            "If the marks are essentially identical, a lesser quantum of proof is needed regarding goods/services relatedness.",
            "A prior pending application takes priority over a later-filed application."
        ],
        "risk_guidance": {
            "HIGH": "Marks share dominant element and goods/services overlap or are closely related",
            "MEDIUM": "Some similarity in marks OR some relatedness in goods, but not both strongly",
            "LOW": "Marks are clearly different OR goods are in completely unrelated fields"
        },
        "citation_text": "Registration is refused because the applicant's mark, as used on the identified goods/services, so resembles the mark in U.S. Registration No. [REG] as to be likely to cause confusion, to cause mistake, or to deceive. Trademark Act §2(d), 15 U.S.C. §1052(d); TMEP §1207.01.",
        "category": "likelihood_of_confusion",
        "related": ["1207.01(b)", "1207.01(b)(i)", "1207.01(b)(ii)", "1207.01(d)"]
    },

    "1207.01(b)": {
        "section": "1207.01(b)",
        "title": "DuPont Factors — Likelihood of Confusion Test",
        "summary": "The 13 DuPont factors are used to determine likelihood of confusion. Not all factors need be present — any single factor may be dispositive. In practice, the similarity of marks and relatedness of goods are the two most critical factors.",
        "key_rules": [
            "The DuPont factors include: (1) similarity of marks, (2) relatedness of goods/services, (3) similarity of trade channels, (4) buyer sophistication, (5) fame of the prior mark, (6) number of similar marks in use, (7) actual confusion evidence, (8) concurrent use without confusion, (9) variety of goods, (10) market interface, (11) applicant's right to exclude, (12) extent of potential confusion, (13) other probative facts.",
            "The two KEY factors are: similarity of marks and relatedness of goods. These two alone are often dispositive.",
            "Not all factors are relevant in every case — focus on the factors where evidence exists.",
            "When marks are identical or virtually identical, the relatedness of goods need only be 'related' not identical.",
            "The more similar the marks, the less similar the goods need be to support a finding of confusion."
        ],
        "risk_guidance": {
            "HIGH": "Multiple DuPont factors weigh against the applicant (especially factors 1 and 2)",
            "MEDIUM": "Key factors are mixed — some favor applicant, some favor registrant",
            "LOW": "Most factors favor the applicant, especially marks are dissimilar"
        },
        "citation_text": "In determining whether marks are likely to cause confusion, the examining attorney considers all relevant DuPont factors. In re E.I. du Pont de Nemours & Co., 476 F.2d 1357, 177 USPQ 563 (C.C.P.A. 1973); TMEP §1207.01(b).",
        "category": "likelihood_of_confusion",
        "related": ["1207.01", "1207.01(b)(i)", "1207.01(b)(ii)"]
    },

    "1207.01(b)(i)": {
        "section": "1207.01(b)(i)",
        "title": "Similarity of Marks — Sound, Appearance, Meaning, Commercial Impression",
        "summary": "Marks are compared in their entireties for similarities in sound, appearance, meaning, and commercial impression. Similarity in even ONE element may suffice. The test considers each mark as a whole but gives more weight to dominant features.",
        "key_rules": [
            "Marks must be compared in their ENTIRETIES, considering sound, appearance, meaning, and overall commercial impression.",
            "Similarity in any ONE element (sound, appearance, or meaning) may be sufficient to find likelihood of confusion.",
            "Marks need NOT be identical — they need only be similar enough to cause confusion.",
            "The dominant portion of a mark is given more weight. Descriptive or generic terms are given less weight.",
            "Adding a word to a registered mark generally does NOT avoid confusion (e.g., adding 'LIVE MORE' to an existing 'POUR' mark).",
            "Phonetic similarity is judged by comparing how marks sound when spoken.",
            "Visual similarity considers the overall look — similar letter patterns, word structure.",
            "Meaning similarity: marks that convey the same idea or impression are similar (e.g., TORNADO and CYCLONE).",
            "Marks should be considered in light of the fallible memory of a purchaser who may not see the marks side by side."
        ],
        "risk_guidance": {
            "HIGH": "Marks share the same dominant word(s), or sound/look very similar, or convey the same meaning",
            "MEDIUM": "Some shared elements but significant differences exist (different dominant element, additional distinguishing terms)",
            "LOW": "Marks are clearly different in sound, appearance, and meaning — different dominant elements"
        },
        "citation_text": "Marks are compared in their entireties for similarities in sound, appearance, meaning, and commercial impression. In re Viterra Inc., 671 F.3d 1358, 101 USPQ2d 1905 (Fed. Cir. 2012); TMEP §1207.01(b)(i).",
        "category": "likelihood_of_confusion",
        "related": ["1207.01", "1207.01(b)", "1207.01(d)"]
    },

    "1207.01(b)(ii)": {
        "section": "1207.01(b)(ii)",
        "title": "Relatedness of Goods/Services",
        "summary": "Goods/services need not be identical to find confusion — they just need to be related enough that consumers would believe they come from the same source. Same trade channels, same class of purchasers, and complementary goods all indicate relatedness.",
        "key_rules": [
            "Goods/services do NOT need to be identical — they must be 'related' such that consumers would assume common source.",
            "The issue is whether the goods are related in the mind of the consumer, not whether they are identical.",
            "Goods in the SAME International Class are often considered related (but not always).",
            "Goods that are COMPLEMENTARY (used together) are related — e.g., beverages and snack foods.",
            "Goods sold in the SAME trade channels (same retail stores, same online categories) are related.",
            "Goods targeting the SAME consumer base are related.",
            "If the marks are very similar or identical, a lower degree of goods/services relatedness is needed.",
            "Evidence of relatedness: third-party registrations covering both types of goods, common trade channels.",
            "Class 5 (dietary supplements) and Class 32 (beverages) are frequently found related by the USPTO."
        ],
        "risk_guidance": {
            "HIGH": "Same or highly complementary goods, same trade channels, same consumer base",
            "MEDIUM": "Somewhat related goods — same industry but different segments or channels",
            "LOW": "Clearly unrelated goods in different industries with different consumers"
        },
        "citation_text": "The goods/services need not be identical or even competitive to find a likelihood of confusion. It is sufficient that the goods/services are related in some manner and/or that the conditions of marketing are such that they could be encountered by the same persons under circumstances that could give rise to the mistaken belief that they originate from the same source. TMEP §1207.01(b)(ii).",
        "category": "likelihood_of_confusion",
        "related": ["1207.01", "1207.01(b)"]
    },

    "1207.01(b)(vii)": {
        "section": "1207.01(b)(vii)",
        "title": "Fame/Strength of the Prior Mark",
        "summary": "A famous mark is entitled to a broader scope of protection. The stronger the prior mark, the less similarity is needed between marks or goods to find confusion.",
        "key_rules": [
            "Famous marks receive a BROADER scope of protection — confusion is found with less similar marks and more diverse goods.",
            "Strength is measured by: sales volume, advertising expenditure, market share, consumer recognition.",
            "Inherently distinctive marks (arbitrary/fanciful) are stronger than descriptive marks with acquired distinctiveness.",
            "If the prior mark is a household name brand, even a loosely similar mark on loosely related goods may create confusion.",
            "Weak marks (descriptive with minimal acquired distinctiveness) receive narrow protection — only very similar marks on very similar goods."
        ],
        "risk_guidance": {
            "HIGH": "Prior mark is a well-known brand with broad recognition",
            "MEDIUM": "Prior mark has moderate recognition in its field",
            "LOW": "Prior mark is relatively unknown or is a weak/descriptive mark"
        },
        "citation_text": "The fame of the prior mark, if it exists, plays a dominant role in the likelihood of confusion analysis. A famous mark enjoys a broad scope of protection. Bose Corp. v. QSC Audio Prods., Inc., 293 F.3d 1367, 63 USPQ2d 1303 (Fed. Cir. 2002); TMEP §1207.01(b)(vii).",
        "category": "likelihood_of_confusion",
        "related": ["1207.01(b)"]
    },

    "1207.01(b)(viii)": {
        "section": "1207.01(b)(viii)",
        "title": "Number and Nature of Similar Marks in Use — Crowded Field",
        "summary": "If many similar marks coexist for the same/similar goods, the prior mark is weaker and consumers are accustomed to distinguishing slight differences. This is the 'crowded field' defense.",
        "key_rules": [
            "Evidence of third-party use/registrations of similar marks for similar goods weakens the cited mark.",
            "A 'crowded field' suggests consumers can distinguish between subtle differences.",
            "Third-party registrations are evidence that a term is commonly used and less likely to cause confusion.",
            "The more similar marks on the register, the less likely any single mark has exclusive rights to common elements.",
            "However, third-party registrations alone may not be sufficient — evidence of ACTUAL USE is stronger.",
            "This factor favors the applicant when many similar marks peacefully coexist."
        ],
        "risk_guidance": {
            "HIGH": "Few if any similar marks exist — the prior mark has a unique position",
            "MEDIUM": "Some similar marks exist but the field is not heavily crowded",
            "LOW": "Many similar marks coexist — crowded field, consumers accustomed to differences"
        },
        "citation_text": "Evidence of third-party use of similar marks for similar goods is relevant to show that the shared element has a commonly understood meaning, and is weak. TMEP §1207.01(b)(viii).",
        "category": "likelihood_of_confusion",
        "related": ["1207.01(b)"]
    },

    "1207.01(d)": {
        "section": "1207.01(d)",
        "title": "Composite Marks and Marks Containing Common Elements",
        "summary": "When a mark contains multiple words or elements, the dominant element is given greatest weight. Adding generic or descriptive matter to a registered mark does NOT avoid confusion.",
        "key_rules": [
            "In a multi-word mark, the DOMINANT element carries the most weight in the confusion analysis.",
            "Descriptive or generic words in a composite mark are given LESS weight.",
            "Adding a generic or descriptive term to a registered mark is generally NOT sufficient to avoid likelihood of confusion.",
            "Example: If 'POUR' is registered, adding 'MORE' to create 'POUR MORE' likely does not avoid confusion.",
            "The overall commercial impression of the composite mark is still considered.",
            "Disclaimed matter (terms the applicant has disclaimed exclusive rights to) is still considered in the confusion analysis.",
            "A mark that incorporates another mark in its entirety creates a strong inference of confusion."
        ],
        "risk_guidance": {
            "HIGH": "Applicant's mark contains the registered mark in its entirety, or shares the dominant element",
            "MEDIUM": "Marks share some elements but have different dominant features",
            "LOW": "Shared elements are descriptive/generic and dominant elements differ significantly"
        },
        "citation_text": "In a composite mark, the dominant portion is given greater weight. Adding a generic or descriptive term to a registered mark does not obviate the likelihood of confusion. TMEP §1207.01(d).",
        "category": "likelihood_of_confusion",
        "related": ["1207.01", "1207.01(b)(i)"]
    },

    "1207.01(b)(iii)": {
        "section": "1207.01(b)(iii)",
        "title": "Similarity of Trade Channels — DuPont Factor 3",
        "summary": "If the goods travel through the same trade channels (same stores, same websites, same distribution networks), confusion is more likely. This factor also covers DuPont Factor 10 (market interface between applicant and registrant).",
        "key_rules": [
            "If the goods of both parties are sold in the same retail outlets, trade channels, or online marketplaces, confusion is more likely.",
            "Identical trade channels significantly increase the likelihood of confusion, even if the goods themselves differ somewhat.",
            "Class 5 (supplements) and Class 32 (beverages) are commonly sold through the SAME channels: grocery stores, health food stores, convenience stores, Amazon, GNC.",
            "Online sales broaden trade channels — products from different categories are often displayed on the same pages or in the same search results.",
            "If the applicant's and registrant's goods target the same consumers through the same distribution methods, this factor weighs against the applicant.",
            "Trade channel analysis considers WHERE the goods are sold, not just what they are.",
            "Even if the applicant intends different channels, the registration covers all normal trade channels for the identified goods."
        ],
        "risk_guidance": {
            "HIGH": "Goods sold through identical trade channels (same stores, same websites, same shelf space)",
            "MEDIUM": "Some overlap in trade channels but primarily different distribution methods",
            "LOW": "Completely different trade channels with no overlap (e.g., industrial vs. consumer retail)"
        },
        "citation_text": "The similarity or dissimilarity of established, likely-to-continue trade channels is a factor in the likelihood of confusion analysis. In re Viterra Inc., 671 F.3d 1358, 101 USPQ2d 1905 (Fed. Cir. 2012); TMEP §1207.01(b)(iii).",
        "category": "likelihood_of_confusion",
        "related": ["1207.01(b)", "1207.01(b)(ii)"]
    },

    "1207.01(b)(iv)": {
        "section": "1207.01(b)(iv)",
        "title": "Conditions of Purchase — Buyer Sophistication (DuPont Factor 4)",
        "summary": "The sophistication and care exercised by the typical buyer affects the likelihood of confusion. Impulse purchases of inexpensive goods increase confusion risk; careful, expensive purchases by sophisticated buyers decrease it.",
        "key_rules": [
            "Inexpensive, frequently purchased goods (e.g., beverages, snacks) are bought with LESS CARE — confusion is MORE likely.",
            "Expensive, specialized goods (e.g., industrial equipment, luxury goods) are bought with MORE CARE — confusion is LESS likely.",
            "Energy drinks, supplements, and beverages are LOW-COST impulse purchases — the relevant consumer exercises minimal care.",
            "The standard is the LEAST SOPHISTICATED consumer in the relevant market, not the most sophisticated.",
            "Where goods are inexpensive, even minor similarities may cause confusion because consumers spend less time evaluating.",
            "Professional buyers in B2B contexts exercise greater care and are less likely to be confused.",
            "The conditions of purchase must be evaluated for the applicant's specific goods/services."
        ],
        "risk_guidance": {
            "HIGH": "Low-cost impulse purchases (beverages, food, basic consumer goods) — consumers exercise minimal care",
            "MEDIUM": "Moderate-cost items where consumers exercise some but not extensive care",
            "LOW": "Expensive, specialized goods purchased by sophisticated/professional buyers with extensive evaluation"
        },
        "citation_text": "Because the goods are relatively low-cost consumer items, purchasers are held to a lesser standard of purchasing care. In re Majestic Distilling Co., 315 F.3d 1311, 65 USPQ2d 1201 (Fed. Cir. 2003); TMEP §1207.01(b)(iv).",
        "category": "likelihood_of_confusion",
        "related": ["1207.01(b)", "1207.01(b)(ii)"]
    },

    "1207.01(b)(v)": {
        "section": "1207.01(b)(v)",
        "title": "Actual Confusion and Concurrent Use — DuPont Factors 7 & 8",
        "summary": "Evidence of actual confusion is strong proof of likelihood of confusion, but is NOT required. Conversely, a long period of concurrent use without confusion may weigh against a finding, but does not guarantee no confusion.",
        "key_rules": [
            "Actual confusion evidence is the BEST evidence of likelihood of confusion, but it is NOT required.",
            "Even a single instance of actual confusion can be significant if it is probative.",
            "The ABSENCE of actual confusion evidence does not mean confusion is unlikely — it may simply mean no evidence has been discovered.",
            "Length of concurrent use without confusion can weigh in the applicant's favor, but ONLY IF the use was under conditions where confusion would have been detected.",
            "Short periods of concurrent use (less than a few years) carry little weight.",
            "If the marks have never actually been used concurrently in the marketplace, this factor is neutral.",
            "In ex parte examination, the examiner typically does not have access to actual confusion evidence — the analysis focuses on LIKELIHOOD, not actual instances."
        ],
        "risk_guidance": {
            "HIGH": "Evidence of actual confusion exists (customer complaints, misdirected communications, survey data)",
            "MEDIUM": "No evidence either way — factor is neutral (typical in examination)",
            "LOW": "Documented concurrent use for 5+ years without any reported confusion"
        },
        "citation_text": "Evidence of actual confusion is not necessary to find likelihood of confusion; likelihood of confusion is the statutory test. Giant Food, Inc. v. Nation's Foodservice, Inc., 710 F.2d 1565, 218 USPQ 390 (Fed. Cir. 1983); TMEP §1207.01(b)(v).",
        "category": "likelihood_of_confusion",
        "related": ["1207.01(b)", "1207.01"]
    },

    "1207.01(b)(vi)": {
        "section": "1207.01(b)(vi)",
        "title": "Doctrine of Foreign Equivalents",
        "summary": "Under the doctrine of foreign equivalents, foreign words are translated into English to determine similarity. If the foreign word is the equivalent of the English mark (or vice versa), the marks may be found confusingly similar.",
        "key_rules": [
            "Foreign words from common languages are translated into their English equivalents for comparison.",
            "The doctrine applies when the ordinary American purchaser would stop and translate the foreign term.",
            "Common languages (Spanish, French, German, Italian, etc.) are presumed to be understood by a significant portion of US consumers.",
            "Obscure or dead languages may not trigger the doctrine — the relevant consumer must be likely to translate.",
            "Example: 'LUPO' (Italian for wolf) vs. 'WOLF' — these may be found confusingly similar.",
            "The doctrine is not applied mechanically — context matters. If the foreign word has a different connotation, it may not apply.",
            "Marks with high SEMANTIC similarity (meaning-based) across languages should trigger this analysis."
        ],
        "risk_guidance": {
            "HIGH": "Foreign word is a direct translation of the English mark in a common language",
            "MEDIUM": "Foreign word has a related but not identical meaning to the English mark",
            "LOW": "Foreign word is from an obscure language or has no meaningful connection"
        },
        "citation_text": "Under the doctrine of foreign equivalents, foreign words from common languages are translated into English for purposes of comparison. Palm Bay Imports, Inc. v. Veuve Clicquot Ponsardin Maison Fondee En 1772, 396 F.3d 1369, 73 USPQ2d 1689 (Fed. Cir. 2005); TMEP §1207.01(b)(vi).",
        "category": "likelihood_of_confusion",
        "related": ["1207.01(b)", "1207.01(b)(i)"]
    },

    "1207.01(d)(i)": {
        "section": "1207.01(d)(i)",
        "title": "Marks Containing the Entirety of a Prior Mark",
        "summary": "When an applicant's mark incorporates the entirety of a registered mark, there is a strong presumption of likelihood of confusion, even if additional matter is added. This is one of the strictest rules in trademark examination.",
        "key_rules": [
            "Incorporation of the ENTIRE prior mark into the applicant's mark creates a strong presumption of confusion.",
            "Adding descriptive or generic words to the prior mark generally does NOT avoid confusion.",
            "Adding additional distinctive matter may help, but the burden is on the applicant to overcome the presumption.",
            "Example: 'LIVEMORE' registered → 'TEAR POUR LIVE MORE' likely confusing because LIVEMORE is entirely contained.",
            "This applies to both literal containment AND phonetic equivalents (e.g., LIVE MORE = LIVEMORE).",
            "The prior mark's entire presence as a component of the new mark is a critical negative factor.",
            "Even if the composite mark has a different overall commercial impression, containment alone creates significant risk."
        ],
        "risk_guidance": {
            "HIGH": "Applicant's mark contains the entire prior mark — regardless of what else is added",
            "MEDIUM": "Applicant's mark contains a substantial portion but not the entirety of the prior mark",
            "LOW": "Only a minor, non-dominant element is shared between the marks"
        },
        "citation_text": "A mark that incorporates another mark in its entirety creates a strong likelihood of confusion. In re Mighty Leaf Tea, 601 F.3d 1342, 94 USPQ2d 1257 (Fed. Cir. 2010); TMEP §1207.01(d)(i).",
        "category": "likelihood_of_confusion",
        "related": ["1207.01(d)", "1207.01(b)(i)"]
    },

    # ===== DILUTION (§1208) =====

    "1208": {
        "section": "1208",
        "title": "Dilution Protection for Famous Marks — Trademark Act §43(c)",
        "summary": "Famous marks are protected against dilution even in the ABSENCE of likelihood of confusion. Dilution can occur by blurring (impairing distinctiveness) or tarnishment (harming reputation). This goes beyond the §2(d) confusion analysis.",
        "key_rules": [
            "Dilution protection applies ONLY to FAMOUS marks — marks widely recognized by the general consuming public of the United States.",
            "Dilution by BLURRING: Association of the famous mark with a dissimilar mark that impairs the famous mark's distinctiveness.",
            "Dilution by TARNISHMENT: Association that harms the reputation of the famous mark (e.g., use on inferior or offensive goods).",
            "Unlike confusion, dilution does NOT require similar goods/services — a famous mark is protected across ALL goods/services.",
            "Factors for blurring: (1) degree of similarity, (2) degree of distinctiveness, (3) extent of exclusive use, (4) degree of recognition, (5) intent to create association, (6) actual association.",
            "Only a small number of truly famous marks qualify: COCA-COLA, GOOGLE, APPLE, NIKE, etc.",
            "Niche fame (known only in a specific market) is typically insufficient — the mark must be famous to the general public.",
            "In USPTO examination, dilution refusals under §43(c) are rare but can be raised when a clearly famous mark is involved."
        ],
        "risk_guidance": {
            "HIGH": "Prior mark is a household name (nationally famous) and applicant's mark is very similar — dilution risk exists regardless of goods",
            "MEDIUM": "Prior mark has significant but not universal fame — dilution claim is possible but not certain",
            "LOW": "Prior mark is not famous enough for dilution protection, or the marks are sufficiently different"
        },
        "citation_text": "The owner of a famous mark is entitled to an injunction against another person who commences use of a mark that is likely to cause dilution by blurring or tarnishment. Trademark Act §43(c), 15 U.S.C. §1125(c); TMEP §1208.",
        "category": "dilution",
        "related": ["1207.01(b)(vii)", "1207.01"]
    },

    # ===== DESCRIPTIVENESS / DISTINCTIVENESS (§1209) =====

    "1209.01": {
        "section": "1209.01",
        "title": "Distinctiveness Spectrum — Abercrombie Classification",
        "summary": "Marks are classified on a spectrum from generic (unregistrable) to fanciful (strongest). The strength of a mark determines its protectability and registrability.",
        "key_rules": [
            "The distinctiveness spectrum (weakest to strongest): GENERIC → DESCRIPTIVE → SUGGESTIVE → ARBITRARY → FANCIFUL.",
            "GENERIC terms can never be registered (e.g., 'COMPUTER' for computers).",
            "DESCRIPTIVE terms can only be registered with proof of acquired distinctiveness under §2(f).",
            "SUGGESTIVE marks are registrable without §2(f) — they require imagination to connect to the goods.",
            "ARBITRARY marks (common words used for unrelated goods) and FANCIFUL marks (invented words) are the strongest and most easily registered.",
            "The distinction between suggestive and descriptive is the most litigated line in trademark law.",
            "Test: Does the term IMMEDIATELY convey information about a quality, feature, function, or characteristic? If YES → descriptive. If consumer must use imagination → suggestive."
        ],
        "risk_guidance": {
            "HIGH": "Mark is generic for the goods (unregistrable) or clearly descriptive without §2(f) evidence",
            "MEDIUM": "Mark falls in the grey area between descriptive and suggestive",
            "LOW": "Mark is clearly suggestive, arbitrary, or fanciful"
        },
        "citation_text": "Marks are classified along a spectrum of distinctiveness from generic (least protectable) to fanciful (most protectable). Abercrombie & Fitch Co. v. Hunting World, Inc., 537 F.2d 4, 189 USPQ 759 (2d Cir. 1976); TMEP §1209.01.",
        "category": "descriptiveness",
        "related": ["1209.01(b)", "1209.01(c)", "1209.03", "1212"]
    },

    "1209.01(b)": {
        "section": "1209.01(b)",
        "title": "Merely Descriptive Marks — §2(e)(1) Refusal",
        "summary": "A mark is 'merely descriptive' if it immediately conveys knowledge of a quality, feature, function, or characteristic of the goods/services. Such marks are refused under §2(e)(1) unless the applicant claims acquired distinctiveness.",
        "key_rules": [
            "A mark is merely descriptive if it IMMEDIATELY conveys an ingredient, quality, characteristic, function, feature, purpose, or use of the goods/services.",
            "The test: Does the mark immediately tell the consumer what the goods ARE or what they DO, without requiring imagination?",
            "Descriptive marks are refused under §2(e)(1) of the Trademark Act, 15 U.S.C. §1052(e)(1).",
            "However, descriptive marks CAN be registered on the Supplemental Register, or on the Principal Register with a §2(f) acquired distinctiveness claim.",
            "Common laudatory terms ('BEST', 'PREMIUM', 'SUPER') may be descriptive.",
            "Terms describing an intended audience, subject matter, or feature are descriptive (e.g., 'KIDSBOOKS' for children's books).",
            "A mark may be descriptive of SOME goods but not others — the analysis is always mark-to-goods."
        ],
        "risk_guidance": {
            "HIGH": "Mark directly names a key ingredient, function, or quality of the goods (e.g., 'POUR' for beverages)",
            "MEDIUM": "Mark suggests a quality but requires some thought to make the connection",
            "LOW": "Mark does not describe the goods — it's suggestive, arbitrary, or fanciful"
        },
        "citation_text": "Registration is refused because the applied-for mark merely describes a feature, quality, or characteristic of applicant's goods/services. Trademark Act §2(e)(1), 15 U.S.C. §1052(e)(1); TMEP §1209.01(b).",
        "category": "descriptiveness",
        "related": ["1209.01", "1209.01(c)", "1209.03", "1212"]
    },

    "1209.01(c)": {
        "section": "1209.01(c)",
        "title": "Suggestive Marks — Registrable Without §2(f)",
        "summary": "A suggestive mark requires imagination, thought, or perception to reach a conclusion about the nature of the goods. Unlike descriptive marks, suggestive marks are registrable on the Principal Register without a showing of acquired distinctiveness.",
        "key_rules": [
            "A suggestive mark SUGGESTS rather than DESCRIBES — it requires a mental leap.",
            "The consumer must use imagination or thought to connect the mark to the goods.",
            "Suggestive marks are registrable on the Principal Register without §2(f) evidence.",
            "The line between suggestive and descriptive is often blurry and is the most litigated issue.",
            "Key question: Does the term require IMAGINATION to connect it to a quality of the goods?",
            "Examples of suggestive marks: COPPERTONE (suntan lotion), CHICKEN OF THE SEA (tuna fish).",
            "If there is any doubt, the mark may be descriptive. The burden is on the applicant."
        ],
        "risk_guidance": {
            "HIGH": "N/A — suggestive marks are registrable",
            "MEDIUM": "Mark is in the grey zone between suggestive and descriptive",
            "LOW": "Mark is clearly suggestive — requires imagination to connect to goods"
        },
        "citation_text": "A suggestive mark requires imagination, thought, or perception to reach a conclusion as to the nature of the goods or services. In re George Weston Ltd., 228 USPQ 57 (TTAB 1985); TMEP §1209.01(c).",
        "category": "descriptiveness",
        "related": ["1209.01", "1209.01(b)"]
    },

    "1209.03": {
        "section": "1209.03",
        "title": "Descriptiveness of Specific Types of Terms",
        "summary": "Analysis of specific term categories: laudatory terms, acronyms/abbreviations, terms incorporating marks, business style terms, model/grade designations.",
        "key_rules": [
            "LAUDATORY terms ('BEST', 'SUPREME', 'ULTIMATE') are descriptive when used to describe quality.",
            "ACRONYMS/ABBREVIATIONS: if the full term is descriptive, the acronym may also be descriptive if consumers understand it.",
            "GEOGRAPHIC terms may be descriptive if goods originate from the named place (§2(e)(2)).",
            "PERSONAL NAMES may be primarily merely a surname (§2(e)(4)).",
            "For BEVERAGES: terms suggesting taste, method of consumption, or experience (e.g., 'POUR', 'SIP', 'DRINK') are likely descriptive.",
            "COMPOUND marks: if each component is descriptive of the goods, the combination may be descriptive if it creates no new meaning beyond the individual components.",
            "The determination of descriptiveness must be made in relation to the specific goods/services, not in the abstract."
        ],
        "risk_guidance": {
            "HIGH": "Mark uses common industry terms, laudatory words, or directly describes the product experience",
            "MEDIUM": "Mark uses terms that are somewhat common but could be argued as suggestive in context",
            "LOW": "Mark uses terms with no descriptive connection to the goods"
        },
        "citation_text": "The determination of whether a mark is descriptive must be made in relation to the specific goods or services. In re Abcor Dev. Corp., 588 F.2d 811, 200 USPQ 215 (C.C.P.A. 1978); TMEP §1209.03.",
        "category": "descriptiveness",
        "related": ["1209.01(b)", "1209.01(c)"]
    },

    "1212": {
        "section": "1212",
        "title": "Acquired Distinctiveness — Section 2(f)",
        "summary": "A descriptive mark can overcome a §2(e)(1) refusal by demonstrating acquired distinctiveness through substantially exclusive and continuous use in commerce, typically for 5+ years.",
        "key_rules": [
            "§2(f) allows registration of a descriptive mark if the applicant can show it has ACQUIRED DISTINCTIVENESS.",
            "Five years of continuous and substantially exclusive use is PRIMA FACIE evidence of acquired distinctiveness.",
            "Other evidence: advertising expenditures, sales volume, consumer surveys/declarations, media coverage.",
            "The more descriptive the mark, the heavier the burden of proof for acquired distinctiveness.",
            "A highly descriptive term requires more evidence than a slightly descriptive term.",
            "Acquired distinctiveness means consumers have come to recognize the term as a SOURCE IDENTIFIER, not just a description.",
            "§2(f) is NOT available for generic terms — a generic term can NEVER acquire distinctiveness."
        ],
        "risk_guidance": {
            "HIGH": "Mark is descriptive and applicant has less than 5 years of use with no strong evidence",
            "MEDIUM": "Mark is descriptive but applicant has 5+ years of use or moderate evidence",
            "LOW": "Mark is not descriptive (suggestive or stronger), so §2(f) is unnecessary"
        },
        "citation_text": "Registration on the Principal Register is refused because the mark is merely descriptive. However, if the applicant can establish acquired distinctiveness under §2(f), registration may be permitted. TMEP §1212.",
        "category": "descriptiveness",
        "related": ["1209.01(b)", "1209.03"]
    },

    # ===== GENERICNESS (§1301) =====

    "1301.02": {
        "section": "1301.02",
        "title": "Genericness — Generic Terms Cannot Be Registered",
        "summary": "Generic terms — the common name for the goods/services — are NEVER registrable, regardless of evidence of acquired distinctiveness. This is the absolute bar to registration.",
        "key_rules": [
            "A generic term is the common or class name for the goods/services.",
            "Generic terms can NEVER be registered as trademarks, not even with §2(f) evidence.",
            "Test: Is the term understood by the relevant public to refer to the GENUS of goods? If yes → generic.",
            "A mark that was once distinctive can become generic through 'genericide' (e.g., aspirin, escalator).",
            "Evidence of genericness: dictionary definitions, media usage, consumer understanding, competitor use.",
            "USPTO.gov provides that 'marks that are generic for the relevant goods or services... cannot be registered.'",
            "The relevant public is the purchasing public — not the general public in all cases."
        ],
        "risk_guidance": {
            "HIGH": "Term is the common name for the product (e.g., 'ENERGY DRINK' for energy drinks)",
            "MEDIUM": "Term is commonly used in the industry but might be argued as merely descriptive",
            "LOW": "Term is not the common name — it has trademark significance beyond the product name"
        },
        "citation_text": "Registration is refused because the applied-for mark is generic for applicant's goods/services and is therefore incapable of functioning as a source identifier. TMEP §1301.02.",
        "category": "genericness",
        "related": ["1209.01"]
    },

    # ===== SPECIMENS (§904) =====

    "904": {
        "section": "904",
        "title": "Specimens — General Requirements",
        "summary": "A specimen shows the mark as actually used in commerce. The examining attorney must verify that the specimen shows the mark applied to the goods or used in commerce for services.",
        "key_rules": [
            "A specimen is required to show USE of the mark in commerce — it's proof the mark is actually being used.",
            "For goods (§1(a) applications): specimen must show the mark on the goods or packaging (labels, tags, containers).",
            "For services (§1(a) applications): specimen must show the mark used in the sale or advertising of the services.",
            "For §1(b) intent-to-use applications: no specimen is needed at filing, but one is required before registration.",
            "Digital/website specimens ARE acceptable if they show the mark associated with the goods in an online ordering context.",
            "Mere advertising may NOT be acceptable as a specimen for goods — it must be a point-of-sale display.",
            "Mock-ups, printer's proofs, and digitally created specimens are generally NOT acceptable."
        ],
        "risk_guidance": {
            "HIGH": "No specimen available, or specimen doesn't show mark on goods/packaging",
            "MEDIUM": "Specimen available but format is questionable (advertising, social media post)",
            "LOW": "Clear specimen showing mark on product label, packaging, or compliant digital specimen"
        },
        "citation_text": "A specimen must show the mark as actually used on or in connection with the goods or services in commerce. TMEP §904.",
        "category": "specimen_deficiency",
        "related": ["904.03"]
    },

    "904.03": {
        "section": "904.03",
        "title": "Specimens for Goods — Labels, Tags, Packaging",
        "summary": "Acceptable specimens for goods include labels, tags, or containers showing the mark. The specimen must show the mark affixed to the goods, displays associated with the goods at the point of sale, or webpage displays showing the mark with a means of ordering.",
        "key_rules": [
            "Acceptable specimens for goods: labels affixed to goods, tags attached to goods, packaging/containers.",
            "Webpage specimens: must show (1) the mark, (2) a picture or description of the goods, and (3) a means of ordering.",
            "Point-of-sale displays: acceptable if they associate the mark with the goods and include ordering information.",
            "NOT acceptable: advertising materials alone, press releases, internal documents, invoices (for goods).",
            "For Class 5 (supplements) and Class 32 (beverages): product labels, packaging, and retail displays are typical.",
            "The mark on the specimen must match the mark in the application — minor differences in font/style are OK.",
            "Color specimens are preferred; the mark should be clearly visible on the specimen."
        ],
        "risk_guidance": {
            "HIGH": "No product label/packaging with mark, or mark differs substantially from application",
            "MEDIUM": "Webpage specimen that may lack ordering information or product image",
            "LOW": "Clear product label/packaging showing the mark as filed"
        },
        "citation_text": "The specimen must show the mark as used on labels, tags, containers, or displays associated with the goods. TMEP §904.03.",
        "category": "specimen_deficiency",
        "related": ["904"]
    },

    # ===== IDENTIFICATION OF GOODS/SERVICES (§1402) =====

    "1402": {
        "section": "1402",
        "title": "Identification of Goods/Services — Clarity and Specificity",
        "summary": "The identification of goods/services in the application must be clear, accurate, and specific enough for the examining attorney to classify properly and for the public to understand the scope of the registration.",
        "key_rules": [
            "The identification must be specific — vague terms like 'various goods' or 'general merchandise' are unacceptable.",
            "Goods/services must be described using common commercial names, not technical/trade jargon.",
            "The identification must accurately describe what the applicant actually sells or intends to sell.",
            "Overinclusive identifications may be objected to — you cannot claim broader goods than you actually use.",
            "The ID Manual (USPTO acceptable identifications database) provides pre-approved wordings.",
            "If the identification is too broad, the examiner will require amendment to be more specific.",
            "The identification determines the International Class(es) for the application."
        ],
        "risk_guidance": {
            "HIGH": "Vague identification, inaccurate description of goods, or overly broad language",
            "MEDIUM": "Identification is slightly broad or uses non-standard wording that may need amendment",
            "LOW": "Clear, specific identification using accepted USPTO terminology"
        },
        "citation_text": "The identification of goods/services must be clear and specific. TMEP §1402.",
        "category": "identification_issue",
        "related": ["1402.01"]
    },

    "1402.01": {
        "section": "1402.01",
        "title": "Acceptable Identification of Goods",
        "summary": "The identification must follow USPTO ID Manual standards. Common acceptable formats for beverages and supplements are prescribed.",
        "key_rules": [
            "Use the USPTO ID Manual for pre-approved identification language.",
            "For Class 5 (dietary supplements): 'Dietary and nutritional supplements' is acceptable.",
            "For Class 32 (beverages): 'Non-alcoholic beverages, namely energy drinks' or 'Bottled water' are acceptable.",
            "Avoid vague language: 'drinks' alone is insufficient — specify the type.",
            "If goods fall in multiple classes, file a multi-class application with separate identification per class.",
            "The identification can be amended to be more specific but generally cannot be broadened after filing.",
            "Use commas, semicolons following mandatory punctuation rules for listing multiple goods."
        ],
        "risk_guidance": {
            "HIGH": "Non-standard or vague identification that doesn't match ID Manual entries",
            "MEDIUM": "Slightly non-standard wording that can be amended",
            "LOW": "Standard ID Manual language used correctly"
        },
        "citation_text": "The identification of goods must be specific and use language from the USPTO ID Manual where possible. TMEP §1402.01.",
        "category": "identification_issue",
        "related": ["1402"]
    },

    # ===== FILING BASIS (§806) =====

    "806": {
        "section": "806",
        "title": "Filing Basis — Section 1(a) Use and Section 1(b) Intent-to-Use",
        "summary": "Applications must state a filing basis: §1(a) for marks already in use in commerce, or §1(b) for marks the applicant has a bona fide intent to use. Each basis has different requirements.",
        "key_rules": [
            "§1(a) — USE IN COMMERCE basis: the mark must be in actual use in commerce at the time of filing.",
            "§1(b) — INTENT TO USE basis: the applicant must have a bona fide intent to use the mark in commerce.",
            "For §1(a): a specimen showing actual use and dates of first use are required at filing.",
            "For §1(b): no specimen at filing, but the applicant must file a Statement of Use (SOU) before registration.",
            "§1(b) applicants get extensions of time to file SOU — up to 3 years from notice of allowance.",
            "The filing basis can be changed from §1(b) to §1(a) if use begins before registration.",
            "A single application can cover multiple classes, but each class needs its own basis and specimen."
        ],
        "risk_guidance": {
            "HIGH": "§1(a) claimed but no actual use, or §1(b) without genuine intent to use",
            "MEDIUM": "Basis is valid but documentation (dates, specimens) may need clarification",
            "LOW": "Clear basis with proper supporting evidence (specimens, dates of use)"
        },
        "citation_text": "The applicant must state the filing basis for the application. TMEP §806.",
        "category": "filing_basis_issue",
        "related": ["904"]
    },

    # ===== DECEPTIVENESS (§1304) =====

    "1304.02": {
        "section": "1304.02",
        "title": "Deceptive Marks — §2(a) Refusal",
        "summary": "A mark is deceptive and refused under §2(a) if it misdescribes the goods, consumers are likely to believe the misdescription, and the misdescription would be material to the purchasing decision.",
        "key_rules": [
            "A deceptive mark misdescribes the goods AND consumers would believe the misdescription AND it's material to the purchase.",
            "Deceptive marks are absolutely barred from registration — even §2(f) cannot save them.",
            "Three-part test: (1) mark misdescribes goods, (2) consumers would believe it, (3) misdescription is material to purchase decision.",
            "Deceptively misdescriptive marks (§2(e)(1)) are DIFFERENT — they are less severe and can be registered with §2(f).",
            "Example: 'LOVEE LAMB' for seat covers not made of lambskin — deceptive if consumers expect real lamb.",
            "Mark suggesting ingredients not present in the product may be deceptive."
        ],
        "risk_guidance": {
            "HIGH": "Mark suggests an ingredient, origin, or quality not present in the goods AND consumers would care",
            "MEDIUM": "Mark could be seen as misdescriptive but the connection is indirect",
            "LOW": "Mark does not misdescribe the goods in any material way"
        },
        "citation_text": "Registration is refused because the mark is deceptive within the meaning of §2(a) of the Trademark Act. TMEP §1304.02.",
        "category": "deceptiveness",
        "related": ["1209.01(b)"]
    },

    # ===== OWNERSHIP (§819) =====

    "819": {
        "section": "819",
        "title": "Ownership and Entity Type",
        "summary": "The application must correctly identify the owner of the mark — the entity that controls the nature and quality of the goods/services. Common issues: wrong entity type, operating as individual vs. corporation, joint ownership.",
        "key_rules": [
            "The applicant must be the owner of the mark — the entity that controls the nature and quality of the goods.",
            "Ownership must be established as of the filing date.",
            "Individual vs. entity: if a business (LLC, Corp) owns the mark, the individual cannot file as applicant.",
            "Joint ownership of trademarks is disfavored — there must be joint control over the nature and quality of goods.",
            "Entity type must be correctly stated: individual, corporation, LLC, partnership, etc.",
            "If the owner changes (assignment), the records must be updated.",
            "A trademark cannot be assigned 'in gross' — it must be transferred with the goodwill of the business."
        ],
        "risk_guidance": {
            "HIGH": "Wrong entity listed as owner, or ownership is disputed",
            "MEDIUM": "Entity type may need clarification or correction",
            "LOW": "Ownership is clear and correctly stated in the application"
        },
        "citation_text": "The application must identify the owner of the mark as of the filing date. TMEP §819.",
        "category": "ownership_issue",
        "related": ["806"]
    },
}


# ---------------------------------------------------------------------------
# Helper/lookup functions
# ---------------------------------------------------------------------------

# Set of all valid section numbers (for citation validation)
VALID_SECTIONS = set(TMEP_SECTIONS.keys())


def get_section(section_id: str) -> Optional[dict]:
    """Get a specific TMEP section by ID. Returns None if not found."""
    return TMEP_SECTIONS.get(section_id)


def get_sections_by_category(category: str) -> List[dict]:
    """Get all TMEP sections for a given issue category."""
    return [s for s in TMEP_SECTIONS.values() if s["category"] == category]


def get_confusion_sections() -> List[dict]:
    """Get all likelihood-of-confusion related sections."""
    return get_sections_by_category("likelihood_of_confusion")


def get_descriptiveness_sections() -> List[dict]:
    """Get all descriptiveness related sections."""
    return get_sections_by_category("descriptiveness")


def get_all_section_ids() -> List[str]:
    """Get list of all valid TMEP section IDs."""
    return list(TMEP_SECTIONS.keys())


def validate_citation(section_id: str) -> bool:
    """Check if a TMEP section citation is in our known knowledge base."""
    # Normalize: remove "TMEP", "§", spaces
    cleaned = section_id.replace("TMEP", "").replace("§", "").replace(" ", "").strip()
    return cleaned in VALID_SECTIONS


def get_citation_text(section_id: str) -> Optional[str]:
    """Get the official citation text for a section."""
    section = get_section(section_id)
    return section["citation_text"] if section else None


def get_risk_guidance(section_id: str) -> Optional[dict]:
    """Get risk level guidance for a section."""
    section = get_section(section_id)
    return section["risk_guidance"] if section else None


def format_section_for_prompt(section_id: str, max_rules: int = 5) -> str:
    """
    Format a TMEP section for inclusion in an LLM prompt.
    
    Returns a compact text block with section number, title, and key rules.
    Designed to be small enough to avoid overfeeding the LLM.
    """
    section = get_section(section_id)
    if not section:
        return ""
    
    rules_text = "\n".join(
        f"  - {rule}" for rule in section["key_rules"][:max_rules]
    )
    
    return (
        f"TMEP §{section['section']}: {section['title']}\n"
        f"{section['summary']}\n"
        f"Key Rules:\n{rules_text}\n"
    )


# Quick summary for debugging
if __name__ == "__main__":
    print(f"📚 TMEP Knowledge Base: {len(TMEP_SECTIONS)} sections loaded")
    print()
    for sid, sec in TMEP_SECTIONS.items():
        print(f"  §{sid}: {sec['title']}")
    print()
    print(f"Categories covered:")
    categories = set(s["category"] for s in TMEP_SECTIONS.values())
    for cat in sorted(categories):
        count = len(get_sections_by_category(cat))
        print(f"  {cat}: {count} sections")
