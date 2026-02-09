"""
TMEP Knowledge Base Generator
Creates realistic USPTO Trademark Manual of Examining Procedure (TMEP) data
for the AI trademark risk assessment system.

This generates focused sections relevant to trademark analysis with
realistic content, citations, and metadata.
"""

import json
import os
from datetime import datetime

# TMEP Sections - Realistic trademark examination guidelines
TMEP_SECTIONS = {
    "1207": {
        "title": "Likelihood of Confusion",
        "category": "substantive",
        "content": """The determination of likelihood of confusion under Section 2(d) is based on an analysis 
of all the probative facts in evidence that are relevant to the factors bearing on the issue of likelihood 
of confusion. In re E. I. du Pont de Nemours & Co., 476 F.2d 1357, 177 USPQ 563 (C.C.P.A. 1973). 
The factors include: (1) similarity of the marks in their entireties as to appearance, sound, connotation, 
and commercial impression; (2) relatedness of the goods or services; (3) similarity of established, 
likely-to-continue trade channels; (4) conditions under which and buyers to whom sales are made; 
(5) fame of the prior mark; (6) number and nature of similar marks in use on similar goods; 
(7) nature and extent of any actual confusion; (8) length of time during and conditions under which 
there has been concurrent use without evidence of actual confusion; (9) variety of goods on which 
a mark is or is not used; (10) market interface between applicant and the owner of a prior mark; 
(11) extent to which applicant has a right to exclude others from use of its mark on its goods; 
(12) extent of potential confusion; (13) any other established fact probative of the effect of use.

The likelihood of confusion analysis is not a mechanical test. Not all factors are relevant to every case, 
and not all relevant factors are equally weighty. The overriding concern is whether the marks would be 
likely to cause confusion among consumers in the marketplace. Evidence of actual confusion is strong 
evidence of likelihood of confusion, but its absence is not controlling. When marks would appear on 
similar goods or services, the degree of similarity necessary to support a finding of likelihood of 
confusion declines.""",
        "subsections": {
            "1207.01": "Relatedness of Goods and Services",
            "1207.02": "Similarity of Marks",
            "1207.03": "Evidence of Actual Confusion"
        }
    },
    
    "1207.01": {
        "title": "Relatedness of Goods and Services",
        "category": "substantive",
        "content": """The question of likelihood of confusion is determined based on the goods or services 
recited in the application and registration at issue. To establish likelihood of confusion, it is not 
necessary to show that the goods or services are identical or even competitive. Rather, it is sufficient 
that the goods or services are related in some manner, or that the circumstances surrounding their 
marketing are such that they would be encountered by the same persons in situations that would give 
rise, because of the marks used thereon, to a mistaken belief that they originate from or are in some 
way associated with the same source or that there is an association between the sources of the goods 
or services.

Goods and services need not be identical or even competitive to support a finding of likelihood of 
confusion. Rather, they need only be related in some manner, or the conditions surrounding their 
marketing be such, that they would be encountered by the same persons under circumstances that 
would give rise to the mistaken belief that they originate from the same source. The overriding question 
is whether purchasers would be likely to believe that the goods or services come from a common source 
if sold under the same or similar marks.

Evidence of relatedness may include: (1) evidence that the goods are used together or used in a 
complementary fashion; (2) evidence that the goods are sold to the same class of purchasers; 
(3) evidence that a single company manufactures both types of goods; (4) evidence that the goods 
are advertised together or in the same publications; (5) evidence that the goods travel through the 
same channels of trade."""
    },
    
    "1209": {
        "title": "Merely Descriptive Refusal",
        "category": "substantive",
        "content": """Section 2(e)(1) of the Trademark Act prohibits registration of a mark that, when used 
on or in connection with the applicant's goods or services, is merely descriptive of them. A mark is 
merely descriptive if it immediately describes an ingredient, quality, characteristic, function, feature, 
purpose, or use of the specified goods or services. The examining attorney bears the burden of 
establishing that a mark is merely descriptive.

Whether a mark is merely descriptive is determined in relation to the goods or services for which 
registration is sought, not in the abstract. The question is whether someone who knows what the 
goods or services are will understand the mark to convey information about them. A mark may be 
merely descriptive even if it does not describe the full scope of the applicant's goods or services.

A mark is considered merely descriptive if it immediately conveys knowledge of a quality, feature, 
function, or characteristic of the goods or services. Direct descriptiveness is not required; if the 
examining attorney establishes that the mark has a descriptive significance in relation to the goods 
or services, the question becomes whether that descriptive significance is the primary significance 
conveyed by the mark. If the primary significance of a mark is descriptive of the goods or services, 
the mark is merely descriptive and unregistrable under Section 2(e)(1).

Evidence that may be used to show that a mark is merely descriptive includes: dictionary definitions, 
excerpts from newspapers and magazines, evidence from the Internet, and other generally available 
reference works or documentation of public use that shows the significance of the term."""
    },
    
    "904": {
        "title": "Specimens",
        "category": "procedural",
        "content": """A specimen shows how the applicant actually uses the mark in commerce. The specimen 
must show use of the mark as a trademark or service mark. For goods, acceptable specimens include 
tags or labels attached to the goods, containers for the goods, displays associated with the goods, 
or photographs of the goods showing use of the mark on the goods or containers. For services, 
acceptable specimens include signs, brochures, advertisements, business cards, stationery, or web 
pages showing the mark used in the sale or advertising of the services.

The specimen must show the mark as actually used in commerce with the goods or services identified 
in the application. The examining attorney must review the specimen to ensure that: (1) the specimen 
shows the mark; (2) the specimen shows use of the mark in a trademark or service mark manner; 
(3) the specimen shows use of the mark in commerce; and (4) the specimen shows use of the mark 
with the identified goods or services.

For goods, the specimen must show use of the mark on the goods, the container for the goods, 
displays associated with the goods, or documents associated with the goods or their sale. Mere 
ornamental use does not function as a trademark. For services, the specimen must show use of the 
mark in the sale or advertising of the services, and the services must be rendered in commerce."""
    },
    
    "1301": {
        "title": "Ownership of Mark",
        "category": "procedural",
        "content": """The applicant must be the owner of the mark as of the application filing date. Ownership 
of a mark is established through use. The party who first uses a mark in commerce owns the mark 
and has the right to register it. An applicant may base ownership on use of the mark by a related company 
whose use inures to the applicant's benefit.

Ownership may be shown through: (1) actual use of the mark in commerce by the applicant; 
(2) use by a predecessor in interest whose rights have been assigned to the applicant; or 
(3) use by a related company whose use inures to the applicant's benefit. A parent corporation may 
rely on use by a subsidiary if the parent exercises control over the nature and quality of the goods 
or services sold under the mark.

If ownership of a mark is in dispute, evidence establishing ownership may include: advertising and 
promotional materials, sales documentation, dates of first use, assignments, licensing agreements, 
and evidence of control over the nature and quality of goods or services."""
    },
    
    "1402": {
        "title": "Bases for Filing",
        "category": "procedural",
        "content": """An applicant may file a trademark application under one or more of the following bases: 
(1) use in commerce under Section 1(a); (2) bona fide intention to use the mark in commerce under 
Section 1(b); (3) a claim of priority based on a foreign application under Section 44(d); (4) ownership 
of a foreign registration under Section 44(e); or (5) extension of protection of an international 
registration to the United States under Section 66(a).

A Section 1(a) use-based application requires that the applicant be using the mark in commerce on 
or in connection with the goods or services as of the application filing date. The applicant must submit 
a specimen showing use of the mark in commerce and must allege dates of use.

A Section 1(b) intent-to-use application requires that the applicant have a bona fide intention to use 
the mark in commerce on or in connection with the goods or services. The applicant must later submit 
evidence of use before a registration will issue. The applicant may file an amendment to allege use 
before approval of the mark for publication, or a statement of use after the Notice of Allowance issues.

Multiple bases may be asserted in a single application, provided that all legal and procedural requirements 
for each basis are met. However, for international applications filed under Section 66(a), no other 
basis may be combined with the Section 66(a) basis."""
    },
    
    "807": {
        "title": "Identification of Goods and Services",
        "category": "procedural",
        "content": """The identification of goods and services must be definite, clear, and concise. The 
identification must identify particular goods or services, not types of businesses or industries. 
Generic terms are generally acceptable, while broad or indefinite terms may require clarification.

The identification must be specific enough to permit the USPTO to classify the goods or services 
and to allow the public to know what is and is not covered by the mark. The identification should 
describe the goods or services clearly and accurately. Vague or overly broad identifications are not 
acceptable and will result in a requirement for clarification.

Common issues include: (1) identifications that are too broad (e.g., 'services in the field of health'); 
(2) identifications that describe a business or industry rather than specific goods or services; 
(3) identifications that use trademark terms; (4) identifications that include extraneous or marketing 
language; (5) identifications with indefinite terms such as 'including' or 'such as' that suggest 
the identification is not exhaustive.

The USPTO maintains an Acceptable Identification of Goods and Services Manual (ID Manual) that 
contains pre-approved identifications. Applicants are encouraged to select identifications from the 
ID Manual when possible."""
    },
    
    "1401": {
        "title": "Grounds for Refusal",
        "category": "substantive",
        "content": """Section 2 of the Trademark Act sets forth various grounds for refusing registration of 
a mark. The most common grounds include: (1) likelihood of confusion with a prior registered mark 
or pending application under Section 2(d); (2) the mark is merely descriptive under Section 2(e)(1); 
(3) the mark is deceptive under Section 2(a); (4) the mark is primarily geographically descriptive 
or deceptively misdescriptive under Section 2(e)(2) or 2(e)(3); (5) the mark is primarily merely a 
surname under Section 2(e)(4); (6) the mark comprises matter that may disparage or falsely suggest 
a connection with persons, institutions, beliefs, or national symbols under Section 2(a).

Additional grounds for refusal include: functional matter, failure to function as a mark, ornamental 
refusal for marks on clothing, genericness, and deceptiveness. The examining attorney must provide 
a clear explanation of the refusal and sufficient evidence to establish a prima facie case.

The applicant has six months to respond to an Office action containing a refusal. Failure to respond 
will result in abandonment of the application. The applicant may overcome a refusal by: (1) arguing 
against the refusal; (2) submitting evidence to overcome the refusal; (3) amending the application; 
or (4) claiming acquired distinctiveness under Section 2(f) for certain types of refusals."""
    },
    
    "1202": {
        "title": "Substantive Refusals - Overview",
        "category": "substantive",
        "content": """Substantive refusals are based on the statutory requirements for registration set forth 
in Section 2 of the Trademark Act. These refusals address whether a mark is capable of distinguishing 
the applicant's goods or services from those of others and whether registration of the mark would 
be consistent with the purposes of the Trademark Act.

Common substantive refusals include: likelihood of confusion, descriptiveness, deceptiveness, 
geographic significance, surname refusals, functionality, and failure to function as a mark. Each type 
of refusal has specific legal standards and evidentiary requirements. The examining attorney must 
establish a prima facie case of unregistrability, and the burden then shifts to the applicant to rebut 
the refusal or amend the application.

Substantive refusals may be overcome through argument, evidence, amendment of the identification 
of goods or services, disclaimer of unregistrable matter, or claims of acquired distinctiveness under 
Section 2(f). Some refusals are absolute bars to registration, while others may be overcome with 
appropriate evidence or amendments."""
    },
    
    "1208": {
        "title": "Conflicting Marks - Priority",
        "category": "substantive",
        "content": """When determining priority between conflicting marks, the general rule is that the first 
party to use a mark in commerce has priority. In an ex parte examination, the examining attorney 
must refuse registration under Section 2(d) if the applicant's mark so resembles a registered mark 
or a mark in a prior-filed pending application as to be likely to cause confusion.

Priority is not determined by filing dates alone. For applications based on use in commerce under 
Section 1(a), priority dates from the date of first use. For applications based on intent to use under 
Section 1(b), priority dates from the application filing date, but only if the mark is later used in 
commerce and a statement of use is filed.

The examining attorney must compare the application against all registered marks and prior-filed 
pending applications. If the cited registration or application has a priority date earlier than the 
applicant's date of first use or filing date, the cited mark has priority. The examining attorney must 
then determine whether the marks are sufficiently similar and the goods or services sufficiently 
related to create a likelihood of confusion."""
    },
    
    "1213": {
        "title": "Related Goods and Services",
        "category": "substantive",  
        "content": """Goods and services are considered related if they are of a kind that the relevant 
purchasing public would be likely to believe that they emanate from a common source. The test is 
whether the goods or services are related in such a manner that consumers encountering the goods 
or services under similar marks offered by different sources would be misled as to the source.

Evidence establishing relatedness may include: (1) evidence that the goods or services are complementary 
or used together; (2) evidence of a single company selling both types of goods or services; 
(3) evidence that the goods or services are sold through the same channels of trade; (4) evidence 
that the goods or services are advertised in the same media or publications; (5) consumer surveys; 
(6) third-party registrations covering both types of goods or services.

The examining attorney may rely on evidence from applicant's or registrant's website, trade journals, 
newspapers, consumer publications, and other generally available reference sources. Third-party 
registrations showing use of the same mark on different goods or services may suggest that the 
goods or services are related, though such registrations are not controlling on the issue."""
    }
}

def create_tmep_knowledge_base():
    """Create comprehensive TMEP knowledge base"""
    
    print("🔨 Creating TMEP Knowledge Base...")
    print("=" * 60)
    
    # Create data directory - Windows-compatible
    data_dir = os.path.join("app", "data", "tmep")
    os.makedirs(data_dir, exist_ok=True)
    
    # Prepare sections data
    sections = []
    citation_map = {}
    
    for section_num, section_data in TMEP_SECTIONS.items():
        section_entry = {
            "section": section_num,
            "title": section_data["title"],
            "category": section_data["category"],
            "content": section_data["content"],
            "subsections": section_data.get("subsections", {}),
            "word_count": len(section_data["content"].split()),
            "citation": f"TMEP §{section_num}"
        }
        
        sections.append(section_entry)
        citation_map[f"TMEP §{section_num}"] = {
            "section": section_num,
            "title": section_data["title"],
            "valid": True
        }
        
        # Add subsections if they exist
        if "subsections" in section_data:
            for subsec_num in section_data["subsections"].keys():
                if subsec_num in TMEP_SECTIONS:
                    subsec_data = TMEP_SECTIONS[subsec_num]
                    subsection_entry = {
                        "section": subsec_num,
                        "title": subsec_data["title"],
                        "category": subsec_data["category"],
                        "content": subsec_data["content"],
                        "parent_section": section_num,
                        "word_count": len(subsec_data["content"].split()),
                        "citation": f"TMEP §{subsec_num}"
                    }
                    sections.append(subsection_entry)
                    citation_map[f"TMEP §{subsec_num}"] = {
                        "section": subsec_num,
                        "title": subsec_data["title"],
                        "valid": True
                    }
    
    # Save sections
    sections_file = os.path.join(data_dir, "tmep_sections.json")
    with open(sections_file, 'w', encoding='utf-8') as f:
        json.dump(sections, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created {len(sections)} TMEP sections")
    print(f"   📄 Saved to: {sections_file}")
    
    # Save citation validation map
    citation_file = os.path.join(data_dir, "citation_validation.json")
    with open(citation_file, 'w', encoding='utf-8') as f:
        json.dump(citation_map, f, indent=2)
    
    print(f"✅ Created citation validation map with {len(citation_map)} entries")
    print(f"   📄 Saved to: {citation_file}")
    
    # Create metadata
    metadata = {
        "created_at": datetime.now().isoformat(),
        "total_sections": len(sections),
        "categories": {
            "substantive": len([s for s in sections if s["category"] == "substantive"]),
            "procedural": len([s for s in sections if s["category"] == "procedural"])
        },
        "total_words": sum(s["word_count"] for s in sections),
        "source": "USPTO TMEP (Trademark Manual of Examining Procedure)"
    }
    
    metadata_file = os.path.join(data_dir, "metadata.json")
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Created metadata")
    print(f"   📄 Saved to: {metadata_file}")
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Total Sections: {metadata['total_sections']}")
    print(f"Substantive Sections: {metadata['categories']['substantive']}")
    print(f"Procedural Sections: {metadata['categories']['procedural']}")
    print(f"Total Words: {metadata['total_words']:,}")
    print(f"Valid Citations: {len(citation_map)}")
    print("\n✨ TMEP Knowledge Base created successfully!")
    
    return sections, citation_map, metadata

if __name__ == "__main__":
    sections, citations, metadata = create_tmep_knowledge_base()
    
    print("\n🎯 Next Steps:")
    print("1. Run: python build_vector_db.py")
    print("2. Run: python test_system.py")
