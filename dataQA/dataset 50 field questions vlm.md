[
{
"id": 1,
"group": "Location, Characteristics & Crack Observation",
"question": "How long is the main crack on this concrete block, and where does it extend from and to?",
"explanation": "Determine the propagation path of the crack to assess whether it only affects one face or cuts through the entire concrete block.",
"keywords": ["crack length", "crack trajectory", "start point", "end point"],
"ai_action": "Measure pixel length, estimate real-world distance, and describe the path from the top edge to the base of the concrete block."
},
{
"id": 2,
"group": "Location, Characteristics & Crack Observation",
"question": "Approximately how many millimeters wide is the crack at its widest point?",
"explanation": "Crack width is a critical factor in deciding whether the component remains safe or has exceeded allowable limits.",
"keywords": ["crack width", "gap size", "crack aperture"],
"ai_action": "Use reference objects in the image (anchor bolts, nuts) to convert pixels to actual dimensions (mm)."
},
{
"id": 3,
"group": "Location, Characteristics & Crack Observation",
"question": "Is this a single continuous crack line or does it branch out into multiple secondary cracks?",
"explanation": "Branching cracks indicate that the concrete region is subject to complex stress distributions or severe shear forces.",
"keywords": ["branched crack", "single crack line", "crack network"],
"ai_action": "Analyze the geometric structure of the crack paths (green/red overlays) to identify branching points."
},
{
"id": 4,
"group": "Location, Characteristics & Crack Observation",
"question": "Is the primary crack orientation vertical, horizontal, or diagonal?",
"explanation": "The orientation helps infer the primary stress type causing the failure (compression, tension, or shear).",
"keywords": ["vertical crack", "horizontal crack", "diagonal crack", "crack orientation"],
"ai_action": "Determine the inclination angle of the crack relative to the vertical axis."
},
{
"id": 5,
"group": "Location, Characteristics & Crack Observation",
"question": "Where is this cracked concrete block situated within the overall structural assembly (bridge bearing, column base, or pedestal)?",
"explanation": "Understand the structural role of the element to evaluate its critical impact on the entire structure.",
"keywords": ["bearing block", "pedestal", "column base", "structural location"],
"ai_action": "Analyze the surrounding context (steel plates, anchor bolts, girders) to correctly classify the element."
},
{
"id": 6,
"group": "Location, Characteristics & Crack Observation",
"question": "Has the crack propagated between the upper concrete block and the lower base pedestal?",
"explanation": "Examine crack propagation across joints between adjacent concrete blocks.",
"keywords": ["crack propagation", "expansion joint", "interface boundary"],
"ai_action": "Inspect the boundary interface between the two concrete elements to see if the crack crosses it."
},
{
"id": 7,
"group": "Location, Characteristics & Crack Observation",
"question": "Do the edges of the crack appear sharp and clean, or are they spalled and crumbled?",
"explanation": "Crumbled edges suggest that the crack occurred long ago and has been subject to ongoing displacement or vibration.",
"keywords": ["crack edges", "concrete spalling", "crumbled edges", "displacement"],
"ai_action": "Zoom into the crack boundary to observe the level of localized surface damage along the fissure."
},
{
"id": 8,
"group": "Location, Characteristics & Crack Observation",
"question": "Is there any concrete segment on the front face at risk of spalling or falling off?",
"explanation": "Assess immediate hazards to personnel or equipment below if a loose concrete chunk detaches.",
"keywords": ["spalling", "detached chunk", "falling hazard", "site safety"],
"ai_action": "Identify and bound concrete segments that are completely enclosed by cracks (detachment risk)."
},
{
"id": 9,
"group": "Location, Characteristics & Crack Observation",
"question": "Does the crack originate from an anchor bolt hole or a corner of the steel plate?",
"explanation": "Sharp corners and bolt holes are stress concentration zones that frequently initiate cracking.",
"keywords": ["stress concentration", "bolt location", "plate edge", "crack origin"],
"ai_action": "Locate the crack's origin point and verify if it coincides with a bolt hole or steel plate corner."
},
{
"id": 10,
"group": "Location, Characteristics & Crack Observation",
"question": "What is the distance from the crack to the nearest anchor bolt?",
"explanation": "Cracks located too close to anchor bolts weaken the concrete embedment and anchorage capacity.",
"keywords": ["distance", "anchor bolt", "embedment capacity"],
"ai_action": "Measure the shortest distance between the crack line and the anchor bolt shank in the image."
},
{
"id": 11,
"group": "Location, Characteristics & Crack Observation",
"question": "Is the concrete surface around the cracked region bulging or protruding outward relative to the original plane?",
"explanation": "Outward bulging indicates internal rebar corrosion expansion pushing the concrete cover outward.",
"keywords": ["surface bulging", "outward deformation", "concrete plane"],
"ai_action": "Observe shadows and surface planarity to detect protruding concrete areas."
},
{
"id": 12,
"group": "Location, Characteristics & Crack Observation",
"question": "Are there surface voids or honeycombing on the concrete block caused by poor compaction during construction?",
"explanation": "Differentiate between initial construction defects (honeycombing) and serviceability degradation.",
"keywords": ["concrete voids", "honeycombing", "construction defect"],
"ai_action": "Identify small scattered voids or pitting on the concrete surface."
},
{
"id": 13,
"group": "Location, Characteristics & Crack Observation",
"question": "Does the crack appear recent (fresh cement color) or old (darkened, dust-accumulated)?",
"explanation": "Helps engineers determine whether the crack formed recently or has been active/dormant over a long period.",
"keywords": ["fresh crack", "aged crack", "crack interior color", "dust accumulation"],
"ai_action": "Compare the internal color of the crack aperture with the external concrete surface."
},
{
"id": 14,
"group": "Location, Characteristics & Crack Observation",
"question": "Is the top steel plate showing signs of cracking or deformation corresponding to the concrete failure?",
"explanation": "Check if deformation is isolated to the concrete or extends to load-bearing steel components.",
"keywords": ["steel plate", "base plate", "steel deformation"],
"ai_action": "Analyze the geometry and morphology of the top steel base plate above the cracked concrete."
},
{
"id": 15,
"group": "Location, Characteristics & Crack Observation",
"question": "What are the estimated overall dimensions (height, width) of the cracked concrete block?",
"explanation": "Evaluate component scale to compute the volume of affected concrete.",
"keywords": ["element dimensions", "height", "width", "scale estimation"],
"ai_action": "Scale visual elements in the photo to estimate length x width x height proportions."
},
{
"id": 16,
"group": "Corrosion, Moisture & Environmental Observation",
"question": "Are the brownish-red stains around and beneath the bolts indicative of active rust?",
"explanation": "Confirm the presence of metal oxidation and rebar/fastener corrosion at the site.",
"keywords": ["brownish-red stain", "rusting", "iron oxidation"],
"ai_action": "Detect characteristic iron-oxide color patches on the concrete surface and nuts."
},
{
"id": 17,
"group": "Corrosion, Moisture & Environmental Observation",
"question": "Is the rust streak running down from the anchor bolts or exuding directly out of the crack?",
"explanation": "Distinguish between surface rust runoff from external hardware and internal rebar corrosion exuding through cracks.",
"keywords": ["rust streak", "crack exudation", "rust source"],
"ai_action": "Trace the flow path of the discoloration to locate its primary source."
},
{
"id": 18,
"group": "Corrosion, Moisture & Environmental Observation",
"question": "Is the concrete surface around the crack wet or showing signs of standing water?",
"explanation": "Moisture retention accelerates concrete degradation and steel reinforcement corrosion.",
"keywords": ["dampness", "standing water", "surface moisture"],
"ai_action": "Analyze surface reflectivity and darkness tone to spot wet patches."
},
{
"id": 19,
"group": "Corrosion, Moisture & Environmental Observation",
"question": "Are there whitish salt deposits (efflorescence) leaching out along the crack edges?",
"explanation": "Efflorescence indicates prolonged water seepage dissolving free lime inside the concrete matrix.",
"keywords": ["white deposits", "efflorescence", "lime leaching", "water seepage"],
"ai_action": "Detect pale white crusts along the crack aperture borders."
},
{
"id": 20,
"group": "Corrosion, Moisture & Environmental Observation",
"question": "Have the large anchor bolts developed thick, flaking rust layers?",
"explanation": "Assess section loss and structural capacity reduction of the anchor bolts.",
"keywords": ["flaking rust", "bolt corrosion", "cross-section loss"],
"ai_action": "Examine the bolt shank surface texture for delaminated oxide scaling."
},
{
"id": 21,
"group": "Corrosion, Moisture & Environmental Observation",
"question": "Is there moss or fungal growth on shaded areas or near the base of the concrete block?",
"explanation": "Biological growth signals chronic dampness and lack of direct sunlight exposure.",
"keywords": ["moss growth", "mould", "high humidity", "base surface"],
"ai_action": "Identify green pigment patches against the gray concrete background."
},
{
"id": 22,
"group": "Corrosion, Moisture & Environmental Observation",
"question": "Are the nuts and washers on the anchor bolts seized together due to rust?",
"explanation": "Evaluate the feasibility of mechanical maintenance or re-tightening on-site.",
"keywords": ["anchor nuts", "washers", "rust seizure", "maintenance access"],
"ai_action": "Zoom into thread interfaces and washer gaps to inspect rust fusion."
},
{
"id": 23,
"group": "Corrosion, Moisture & Environmental Observation",
"question": "Is the surface grime composed of general dirt/dust or industrial grease and oil?",
"explanation": "Oil and grease impair surface bonding during potential epoxy injection or sealant repair.",
"keywords": ["grease", "industrial grime", "dirt layer", "surface bonding"],
"ai_action": "Analyze color tone and sheen to differentiate dry dust from oily film."
},
{
"id": 24,
"group": "Corrosion, Moisture & Environmental Observation",
"question": "Is this concrete element fully exposed outdoor or sheltered by an overhead structure?",
"explanation": "Assess the severity of direct environmental exposure (rain cycles, UV, thermal expansion).",
"keywords": ["outdoor exposure", "sheltered structure", "weathering impact"],
"ai_action": "Observe ambient lighting and background foliage to infer shelter status."
},
{
"id": 25,
"group": "Corrosion, Moisture & Environmental Observation",
"question": "Are there dark water run-off stains running vertically along the face of the concrete?",
"explanation": "Identify natural rainwater runoff pathways across the structural element.",
"keywords": ["dark water stains", "runoff trail", "drainage path"],
"ai_action": "Map vertical dark streaks extending from top to bottom on the concrete face."
},
{
"id": 26,
"group": "Corrosion, Moisture & Environmental Observation",
"question": "Is the previous paint or protective coating peeling off in patches?",
"explanation": "Inspect the integrity of existing protective anti-carbonation or waterproofing coatings.",
"keywords": ["protective coating", "peeling paint", "waterproofing failure"],
"ai_action": "Identify flaking or peeling film layers on the concrete surface."
},
{
"id": 27,
"group": "Corrosion, Moisture & Environmental Observation",
"question": "Is there a gap between the steel plate and the concrete block allowing water entry?",
"explanation": "Gaps serve as direct channels for rainwater to penetrate anchor bolt embedments and concrete interiors.",
"keywords": ["interface gap", "bearing plate gap", "water ingress pathway"],
"ai_action": "Inspect the contact seam between steel and concrete for visible voids."
},
{
"id": 28,
"group": "Corrosion, Moisture & Environmental Observation",
"question": "Are loose rust flakes from the bolts dropping onto the lower concrete pedestal?",
"explanation": "Determines if corrosion has reached an advanced stage of material disintegration.",
"keywords": ["rust debris", "flaking scale", "material disintegration"],
"ai_action": "Detect fallen brown oxide particles lying on horizontal ledge surfaces."
},
{
"id": 29,
"group": "Corrosion, Moisture & Environmental Observation",
"question": "Does surrounding vegetation create a humid microclimate around the component?",
"explanation": "Nearby trees/brush retain moisture, accelerating localized degradation.",
"keywords": ["microclimate", "surrounding vegetation", "ambient humidity"],
"ai_action": "Identify foliage and green background elements near the structural member."
},
{
"id": 30,
"group": "Corrosion, Moisture & Environmental Observation",
"question": "Is there visual evidence of surface pitting or chemical degradation on the concrete?",
"explanation": "Evaluate whether the concrete matrix suffers from aggressive environmental or chemical attack.",
"keywords": ["surface pitting", "chemical attack", "surface roughness"],
"ai_action": "Analyze micro-texture and surface roughness variations on the concrete face."
},
{
"id": 31,
"group": "Mechanical Fasteners & Connection Assembly",
"question": "How many total anchor bolts are visible in this photograph?",
"explanation": "Count the fasteners to determine connection group layout and redundancy.",
"keywords": ["bolt count", "anchor studs", "object counting"],
"ai_action": "Detect and accurately count all exposed anchor bolts in the frame."
},
{
"id": 32,
"group": "Mechanical Fasteners & Connection Assembly",
"question": "Is any nut loose or showing a visible gap above the top bearing plate?",
"explanation": "Loose nuts eliminate clamping force, compromising joint stability and load distribution.",
"keywords": ["loose nut", "gap under nut", "clamping force"],
"ai_action": "Inspect the contact area between the bottom face of the nut and the steel plate."
},
{
"id": 33,
"group": "Mechanical Fasteners & Connection Assembly",
"question": "Are any of the anchor bolts bent, tilted, or misaligned from the vertical axis?",
"explanation": "Bent studs indicate exposure to excessive shear forces or lateral displacement.",
"keywords": ["bent bolt", "misalignment", "shear deformation"],
"ai_action": "Check the straightness and vertical alignment of each bolt shank."
},
{
"id": 34,
"group": "Mechanical Fasteners & Connection Assembly",
"question": "What is the estimated thickness of the steel bearing base plate resting on the concrete?",
"explanation": "Estimate steel plate sizing to evaluate load distribution capacity.",
"keywords": ["plate thickness", "bearing plate", "steel member dimension"],
"ai_action": "Compare steel plate thickness against known bolt diameter to estimate dimension in mm."
},
{
"id": 35,
"group": "Mechanical Fasteners & Connection Assembly",
"question": "How much threaded length extends above the top nut on the anchor bolts?",
"explanation": "Ensure sufficient thread engagement for code-compliant structural fastening.",
"keywords": ["thread engagement", "exposed threads", "connection code safety"],
"ai_action": "Estimate thread extension length beyond the upper nut."
},
{
"id": 36,
"group": "Mechanical Fasteners & Connection Assembly",
"question": "Does this cracked concrete block rest directly on a larger lower foundation pedestal?",
"explanation": "Identify the load transfer hierarchy from the upper bearing pad to the lower sub-structure.",
"keywords": ["pedestal base", "concrete pad", "load transfer hierarchy"],
"ai_action": "Analyze concrete stratification from top to bottom within the image frame."
},
{
"id": 37,
"group": "Mechanical Fasteners & Connection Assembly",
"question": "Is the top steel plate warped or lifted at any corner off the concrete surface?",
"explanation": "Warping indicates uneven load distribution, prying action, or local concrete crush underneath.",
"keywords": ["plate warping", "uneven bearing", "prying force"],
"ai_action": "Compare clearance gap uniformity at all four corners of the plate."
},
{
"id": 38,
"group": "Mechanical Fasteners & Connection Assembly",
"question": "Are there circular wear marks around the nuts suggesting previous rotation under load?",
"explanation": "Indicates fastener slippage or rotational movement during cyclic dynamic loading.",
"keywords": ["wear ring", "nut rotation", "dynamic slippage"],
"ai_action": "Look for concentric scoring or circular scratches around the nut perimeter."
},
{
"id": 39,
"group": "Mechanical Fasteners & Connection Assembly",
"question": "Do the anchor bolts feature coarse pitch or fine pitch thread profiles?",
"explanation": "Identify hardware specifications for replacement or load verification purposes.",
"keywords": ["thread pitch", "coarse thread", "fine thread"],
"ai_action": "Observe thread spacing density along the exposed bolt shank."
},
{
"id": 40,
"group": "Mechanical Fasteners & Connection Assembly",
"question": "Does this concrete block appear to be precast or cast-in-place?",
"explanation": "Understand construction methodology and cold-joint interface behavior around the block.",
"keywords": ["precast concrete", "cast-in-place", "construction joint"],
"ai_action": "Inspect surface texture and corner chamfers to infer casting method."
},
{
"id": 41,
"group": "Overall Inspection Context & Visual Scene Description",
"question": "Can you provide a brief summary of what this photo shows for an off-site engineer?",
"explanation": "Generate an instant executive summary for inclusion in site inspection logs.",
"keywords": ["executive summary", "site overview", "inspection log"],
"ai_action": "Summarize clearly: Severely cracked concrete bearing block with corroded anchor bolt connection."
},
{
"id": 42,
"group": "Overall Inspection Context & Visual Scene Description",
"question": "Was this image taken from a low angle, eye-level, or high angle perspective?",
"explanation": "Establish camera orientation perspective to correctly interpret spatial relationships.",
"keywords": ["camera perspective", "low angle", "eye level", "high angle"],
"ai_action": "Analyze line convergence and vanishing points to identify perspective type."
},
{
"id": 43,
"group": "Overall Inspection Context & Visual Scene Description",
"question": "Were the lighting conditions during photo capture harsh sunlight or overcast/shadowed?",
"explanation": "Lighting affects crack contrast; harsh shadows can mask secondary hairline cracks.",
"keywords": ["lighting condition", "harsh sunlight", "overcast", "shadow contrast"],
"ai_action": "Inspect shadow sharpness cast by bolts and plates to infer light source."
},
{
"id": 44,
"group": "Overall Inspection Context & Visual Scene Description",
"question": "Is the image blurry or out of focus around the primary cracked region?",
"explanation": "Assess image quality compliance for technical forensic reporting.",
"keywords": ["image sharpness", "motion blur", "out of focus", "photo quality"],
"ai_action": "Evaluate pixel-level sharpness around the central crack bounding box."
},
{
"id": 45,
"group": "Overall Inspection Context & Visual Scene Description",
"question": "Are there any physical obstructions (cables, debris, equipment) blocking the view of the crack?",
"explanation": "Verify line-of-sight completeness to ensure no hidden damage sections exist.",
"keywords": ["obstruction", "line of sight", "blocked view"],
"ai_action": "Scan for foreign objects overlapping the crack path."
},
{
"id": 46,
"group": "Overall Inspection Context & Visual Scene Description",
"question": "Does the overall concrete color suggest aged, weathered concrete or newer material?",
"explanation": "Aged concrete exhibits dark gray weathering and carbonation patina; newer concrete is light gray.",
"keywords": ["concrete color", "weathering patina", "material age"],
"ai_action": "Analyze surface hue and tone to infer relative material age."
},
{
"id": 47,
"group": "Overall Inspection Context & Visual Scene Description",
"question": "What is the 3D geometric shape of the cracked concrete block (cuboidal, cylindrical, tapered pad)?",
"explanation": "Model component geometry for volumetric estimation and finite element modeling.",
"keywords": ["3D geometry", "cuboidal pad", "component shape"],
"ai_action": "Classify the spatial 3D shape of the concrete element."
},
{
"id": 48,
"group": "Overall Inspection Context & Visual Scene Description",
"question": "Are there any chalk markings, paint indicators, or crack gauges left by previous inspectors?",
"explanation": "Check if this specific damage was previously audited or monitored manually.",
"keywords": ["inspection marking", "chalk line", "crack gauge"],
"ai_action": "Scan concrete faces for artificial markings, numbers, or attached tell-tale gauges."
},
{
"id": 49,
"group": "Overall Inspection Context & Visual Scene Description",
"question": "How would you visually grade the severity of this damage (Minor, Moderate, Severe, Critical)?",
"explanation": "Provide an immediate visual condition rating based on site observation.",
"keywords": ["visual rating", "damage severity", "condition state"],
"ai_action": "Synthesize crack width, extent, and corrosion level to assign a grade (e.g., Severe/Critical)."
},
{
"id": 50,
"group": "Overall Inspection Context & Visual Scene Description",
"question": "If taking a follow-up photo, should the engineer step back for context or zoom closer to a specific zone?",
"explanation": "Provide field capture recommendations to optimize downstream VLM analysis.",
"keywords": ["photo recommendation", "field capture", "macro shot", "context view"],
"ai_action": "Recommend taking a close-up macro of the widest crack tip and a wide contextual shot of the support."
},
{
"id": 51,
"group": "Structural Integrity & Load Capacity",
"question": "Are there signs of crushing or compressive failure along the top contact zone of the concrete block?",
"explanation": "Determine if the upper load is causing localized crushing failure due to high bearing stress.",
"keywords": ["crushing failure", "compressive load", "bearing stress", "top contact"],
"ai_action": "Examine the contact interface between the steel base plate and concrete for crushed concrete powder or fragment loss."
},
{
"id": 52,
"group": "Structural Integrity & Load Capacity",
"question": "Does the crack alignment suggest eccentric loading on the anchor bolt group?",
"explanation": "Unbalanced loading forces one side of the connection to carry higher stress, leading to asymmetric cracking.",
"keywords": ["eccentric loading", "asymmetric crack", "load distribution", "bolt group"],
"ai_action": "Analyze relative crack patterns and gap widths around different bolts across the plate."
},
{
"id": 53,
"group": "Structural Integrity & Load Capacity",
"question": "Is there any evidence of shear displacement or vertical offset across the crack faces?",
"explanation": "A vertical offset along the crack line indicates shear failure rather than pure tensile splitting.",
"keywords": ["shear displacement", "vertical offset", "crack shear", "faulting"],
"ai_action": "Measure relative step-change or displacement across opposite sides of the crack line."
},
{
"id": 54,
"group": "Structural Integrity & Load Capacity",
"question": "Does the concrete show signs of freeze-thaw scaling or surface micro-cracking networks?",
"explanation": "Freeze-thaw cycles cause expansion in saturated concrete, leading to surface scaling and weakening.",
"keywords": ["freeze-thaw", "surface scaling", "micro-cracking", "map cracking"],
"ai_action": "Scan for shallow surface scaling and spider-web micro-crack patterns across the block face."
},
{
"id": 55,
"group": "Structural Integrity & Load Capacity",
"question": "Is internal reinforcement (rebar) exposed within the open crack aperture?",
"explanation": "Exposed steel rebar accelerates corrosion and indicates complete concrete cover failure.",
"keywords": ["exposed rebar", "reinforcement steel", "cover loss", "internal exposure"],
"ai_action": "Inspect the interior cavity of wide cracks for metallic rebar elements or dark steel cross-sections."
},
{
"id": 56,
"group": "Structural Integrity & Load Capacity",
"question": "Is the steel base plate resting uniformly on the grout bed, or is there localized edge lifting?",
"explanation": "Non-uniform bearing causes stress concentration on specific areas of the concrete block.",
"keywords": ["grout bed", "uniform bearing", "edge lifting", "contact area"],
"ai_action": "Inspect the gap uniformity along the entire perimeter interface between steel plate and concrete grout."
},
{
"id": 57,
"group": "Structural Integrity & Load Capacity",
"question": "Are there secondary diagonal shear cracks forming near the outer corners of the pedestal?",
"explanation": "Diagonal corner cracks often signal edge breakout failure under anchor shear loading.",
"keywords": ["edge breakout", "corner crack", "diagonal shear", "anchor failure"],
"ai_action": "Detect diagonal cracking paths extending from anchor locations toward the outer corners."
},
{
"id": 58,
"group": "Structural Integrity & Load Capacity",
"question": "Is there any visible deflection or bending in the supported steel girder above?",
"explanation": "Evaluate whether concrete pedestal deterioration has resulted in structural alignment changes above.",
"keywords": ["girder deflection", "steel bending", "alignment shift", "upper structure"],
"ai_action": "Check straightness of overhead horizontal steel members relative to the reference frame."
},
{
"id": 59,
"group": "Structural Integrity & Load Capacity",
"question": "Does the damage configuration indicate thermal expansion/contraction fatigue?",
"explanation": "Repeated temperature movement can cause cyclic fatigue cracks near fixed structural bearings.",
"keywords": ["thermal expansion", "cyclic fatigue", "bearing movement", "temperature crack"],
"ai_action": "Assess alignment of crack paths with expected directional movement of thermal bearings."
},
{
"id": 60,
"group": "Structural Integrity & Load Capacity",
"question": "Is there evidence of previous structural retrofits, such as steel jackets or carbon fiber wrapping?",
"explanation": "Identify prior repair attempts to evaluate if previous interventions have failed or deteriorated.",
"keywords": ["retrofit", "carbon fiber", "steel jacket", "repair history"],
"ai_action": "Scan around the concrete element for external composite wraps, steel angles, or patch materials."
},
{
"id": 61,
"group": "Maintenance, Remediation & Repair Suitability",
"question": "Is the crack wide enough to perform low-pressure epoxy injection?",
"explanation": "Epoxy injection requires a minimum crack width (typically > 0.2 mm) for successful adhesive flow.",
"keywords": ["epoxy injection", "crack injection", "repair method", "viscosity"],
"ai_action": "Verify if estimated crack aperture meets threshold requirements for resin injection."
},
{
"id": 62,
"group": "Maintenance, Remediation & Repair Suitability",
"question": "Would concrete patch repair require partial demolition of the damaged corner?",
"explanation": "Loose and micro-cracked concrete must be chipped away back to sound concrete before patching.",
"keywords": ["concrete patching", "hydro-demolition", "chipping", "sound concrete"],
"ai_action": "Assess the boundaries of compromised concrete to estimate cut-back volume."
},
{
"id": 63,
"group": "Maintenance, Remediation & Repair Suitability",
"question": "Is there sufficient clearance around the assembly for installing dynamic crack monitoring sensors?",
"explanation": "Monitoring ongoing crack movement requires mounting tell-tale gauges or LVDT sensors.",
"keywords": ["crack monitoring", "sensor installation", "clearance", "tell-tale gauge"],
"ai_action": "Evaluate flat surface availability around the crack for sensor bracket attachment."
},
{
"id": 64,
"group": "Maintenance, Remediation & Repair Suitability",
"question": "Does the anchor bolt assembly require full thread cleaning and re-torquing?",
"explanation": "Corroded threads must be wire-brushed and lubricated before verifying torque specifications.",
"keywords": ["thread cleaning", "re-torquing", "wire brush", "bolt maintenance"],
"ai_action": "Inspect thread condition for surface rust accumulation requiring mechanical cleaning."
},
{
"id": 65,
"group": "Maintenance, Remediation & Repair Suitability",
"question": "Is the surface suitable for applying an elastic elastomeric coating after crack sealing?",
"explanation": "Elastomeric coatings accommodate minor future movement while preventing water ingress.",
"keywords": ["elastomeric coating", "waterproofing", "surface sealing", "protective membrane"],
"ai_action": "Check surface cleanliness, flaking layers, and smoothness for coating adhesion."
},
{
"id": 66,
"group": "Maintenance, Remediation & Repair Suitability",
"question": "Will temporary shoring or jacking be necessary prior to performing structural repairs?",
"explanation": "If the concrete block supports major live loads, load relief via hydraulic jacks may be mandatory during repair.",
"keywords": ["temporary shoring", "hydraulic jack", "load relief", "structural support"],
"ai_action": "Analyze load severity and component degradation to assess need for structural jacking."
},
{
"id": 67,
"group": "Maintenance, Remediation & Repair Suitability",
"question": "Are anchor replacement bolts required due to severe cross-sectional area loss?",
"explanation": "If bolt necking or pitting exceeds safety thresholds, complete anchor replacement is mandatory.",
"keywords": ["bolt replacement", "section loss", "corrosion pitting", "anchor replacement"],
"ai_action": "Estimate percentage of effective bolt diameter loss caused by rust flaking."
},
{
"id": 68,
"group": "Maintenance, Remediation & Repair Suitability",
"question": "Can high-strength non-shrink grout be poured under the base plate to restore bearing contact?",
"explanation": "Void spaces under bearing plates require flowable non-shrink grout underpouring.",
"keywords": ["non-shrink grout", "underpouring", "grout bed repair", "bearing restoration"],
"ai_action": "Check for voids, clearance height, and accessibility under the steel plate."
},
{
"id": 69,
"group": "Maintenance, Remediation & Repair Suitability",
"question": "Is the area around the crack accessible for abrasive sandblasting or wire brushing?",
"explanation": "Surface preparation standards require clean aggregate exposure prior to repair material application.",
"keywords": ["surface preparation", "sandblasting", "abrasive cleaning", "repair adhesion"],
"ai_action": "Assess spatial clearance around the damaged zone for power tool access."
},
{
"id": 70,
"group": "Maintenance, Remediation & Repair Suitability",
"question": "Are there signs of active alkali-silica reaction (ASR) gel exuding from the concrete cracks?",
"explanation": "ASR gel expansion creates widespread map cracking and requires specialized chemical mitigation.",
"keywords": ["alkali-silica reaction", "ASR gel", "map cracking", "chemical expansion"],
"ai_action": "Detect glossy or translucent gelatinous deposits along crack margins."
},
{
"id": 71,
"group": "Detailed Material & Component Analysis",
"question": "What is the primary material composition of the upper base plate (galvanized steel, painted structural steel, stainless steel)?",
"explanation": "Identify material type to determine corrosion resistance and compatibility with repair hardware.",
"keywords": ["material composition", "galvanized steel", "structural steel", "plate finish"],
"ai_action": "Examine surface sheen, spall color, and oxidation layer characteristics."
},
{
"id": 72,
"group": "Detailed Material & Component Analysis",
"question": "Does the concrete aggregate appear exposed due to surface erosion or paste loss?",
"explanation": "Erosion of the cement paste exposes coarse aggregates, accelerating carbonation depth.",
"keywords": ["exposed aggregate", "cement paste loss", "surface erosion", "carbonation"],
"ai_action": "Identify individual stone particles visible on the abraded concrete face."
},
{
"id": 73,
"group": "Detailed Material & Component Analysis",
"question": "Are there rubber or elastomeric bearing pads installed between the steel plate and concrete?",
"explanation": "Elastomeric pads accommodate rotation and thermal movement, isolating concrete from direct local peak stress.",
"keywords": ["elastomeric pad", "bearing pad", "neoprene", "stress distribution"],
"ai_action": "Look for black rubber layers positioned between steel components and concrete."
},
{
"id": 74,
"group": "Detailed Material & Component Analysis",
"question": "Is the washer beneath the anchor nut flat, bevelled, or split-lock type?",
"explanation": "Verify correct washer hardware selection for structural joint integrity.",
"keywords": ["washer type", "bevelled washer", "flat washer", "lock washer"],
"ai_action": "Examine shape, thickness, and slope profile of the washer under the nut."
},
{
"id": 75,
"group": "Detailed Material & Component Analysis",
"question": "Are there signs of galvanic corrosion at the contact interface between dissimilar metals?",
"explanation": "Contact between different metal alloys in moist environments accelerates localized electrolytic corrosion.",
"keywords": ["galvanic corrosion", "dissimilar metals", "electrolytic decay", "metal contact"],
"ai_action": "Inspect joint seams between differing metal components for concentrated rust formation."
},
{
"id": 76,
"group": "Detailed Material & Component Analysis",
"question": "What is the estimated aggregate size visible in the spalled concrete region?",
"explanation": "Coarse aggregate sizing informs maximum aggregate size rules for replacement concrete mixes.",
"keywords": ["aggregate size", "coarse aggregate", "concrete mix", "spall surface"],
"ai_action": "Measure visible stone particle cross-sections against known bolt dimensions."
},
{
"id": 77,
"group": "Detailed Material & Component Analysis",
"question": "Is there any plastic or grout shim pack visible underneath the steel base plate?",
"explanation": "Shim packs are used during alignment but can cause localized stress concentration if left permanently.",
"keywords": ["shim pack", "leveling shims", "alignment", "stress point"],
"ai_action": "Detect thin metal or plastic plate stacks inserted beneath the main bearing plate."
},
{
"id": 78,
"group": "Detailed Material & Component Analysis",
"question": "Does the concrete surface show carbonation discoloration testing marks or carbonated layer signs?",
"explanation": "Carbonation neutralizes concrete alkalinity, leading to loss of rebar passivation.",
"keywords": ["carbonation", "alkalinity loss", "concrete passivation", "pH depth"],
"ai_action": "Identify distinct color boundary layers on freshly exposed concrete fracture faces."
},
{
"id": 79,
"group": "Detailed Material & Component Analysis",
"question": "Are double nuts (jam nuts) installed on the anchor bolts to prevent vibration loosening?",
"explanation": "High-vibration structures require lock nut configurations to maintain joint pre-load.",
"keywords": ["double nut", "jam nut", "vibration resistance", "pre-load"],
"ai_action": "Count vertical nut layers stacked on each exposed bolt shank."
},
{
"id": 80,
"group": "Detailed Material & Component Analysis",
"question": "Is there evidence of sealant or caulk applied around the base plate perimeter in the past?",
"explanation": "Perimeter sealants prevent water ingress under base plates but can fail over time.",
"keywords": ["perimeter sealant", "caulking", "joint seal", "waterproof barrier"],
"ai_action": "Identify flexible bead lines along the seam between metal and concrete."
},
{
"id": 81,
"group": "Safety, Risk Assessment & Hazard Identification",
"question": "Is this damaged support structure located directly above a public pedestrian walkway or roadway?",
"explanation": "High-consequence locations elevate risk levels due to potential falling debris or structural collapse hazards.",
"keywords": ["public safety", "walkway hazard", "roadway risk", "falling debris"],
"ai_action": "Examine background surroundings for traffic lanes, sidewalks, or pedestrian clearance zones."
},
{
"id": 82,
"group": "Safety, Risk Assessment & Hazard Identification",
"question": "Does the extent of cracking indicate an immediate risk of loss of structural load capacity?",
"explanation": "Determine whether emergency temporary shoring is required to prevent progressive collapse.",
"keywords": ["collapse risk", "capacity loss", "emergency shoring", "critical safety"],
"ai_action": "Evaluate combined crack network severity relative to primary compression paths."
},
{
"id": 83,
"group": "Safety, Risk Assessment & Hazard Identification",
"question": "Are sharp rust flakes or jagged concrete edges presenting an immediate injury risk to maintenance personnel?",
"explanation": "Identify localized physical hazards for technicians working in close proximity.",
"keywords": ["sharp edges", "personnel hazard", "injury risk", "site safety"],
"ai_action": "Identify protruding sharp metallic scale or pointed concrete fragments."
},
{
"id": 84,
"group": "Safety, Risk Assessment & Hazard Identification",
"question": "Is there any electrical conduit or grounding wire attached to the corroded assembly?",
"explanation": "Verify presence of electrical hazards or grounding system disruptions attached to damaged steel.",
"keywords": ["grounding wire", "electrical conduit", "electrical hazard", "stray current"],
"ai_action": "Scan for copper wire straps, conduit clamps, or electrical grounding leads."
},
{
"id": 85,
"group": "Safety, Risk Assessment & Hazard Identification",
"question": "Does the severity of degradation warrant restricted load limits on the supported structure?",
"explanation": "Engineers must impose immediate traffic or load restrictions if safety margins are compromised.",
"keywords": ["load restriction", "weight limit", "safety margin", "traffic control"],
"ai_action": "Synthesize structural defect density to recommend operational load restrictions."
},
{
"id": 86,
"group": "Safety, Risk Assessment & Hazard Identification",
"question": "Are there signs of structural movement that could compromise nearby utility pipes or conduits?",
"explanation": "Differential settlement or shift can shear adjacent gas, water, or electrical lines.",
"keywords": ["utility hazard", "differential settlement", "pipe shear", "conduit risk"],
"ai_action": "Inspect adjacent utility lines for signs of strain, bending, or displacement."
},
{
"id": 87,
"group": "Safety, Risk Assessment & Hazard Identification",
"question": "Is access to this inspection point restricted by confined space or height safety hazards?",
"explanation": "Guide maintenance crews on required personal protective equipment (PPE) and rigging needs.",
"keywords": ["confined space", "height safety", "access restriction", "fall protection"],
"ai_action": "Analyze spatial surrounds to classify safety access requirements (harness, scaffolding)."
},
{
"id": 88,
"group": "Safety, Risk Assessment & Hazard Identification",
"question": "Is the corrosion product expanding in a way that causes prying stress on surrounding fasteners?",
"explanation": "Rust expansion (rust packing) exerts massive hydraulic-like forces that can snap nearby bolts.",
"keywords": ["rust packing", "prying stress", "expansion pressure", "bolt snapping"],
"ai_action": "Look for outward displacement caused by thick oxide layers build-up between plates."
},
{
"id": 89,
"group": "Safety, Risk Assessment & Hazard Identification",
"question": "Does the cracked block show signs of progressive movement under dynamic traffic loading?",
"explanation": "Dynamic movement accelerates fatigue failure and requires immediate stabilization.",
"keywords": ["dynamic movement", "traffic loading", "fatigue failure", "vibration displacement"],
"ai_action": "Check for fresh bright-colored concrete dust indicating active rubbing under movement."
},
{
"id": 90,
"group": "Safety, Risk Assessment & Hazard Identification",
"question": "What urgency level should be assigned for field engineering reinspection (24 hours, 7 days, 30 days)?",
"explanation": "Assign action timeframe based on automated risk prioritization algorithms.",
"keywords": ["urgency level", "reinspection window", "risk priority", "action timeframe"],
"ai_action": "Calculate overall risk index to recommend formal reinspection timeline."
},
{
"id": 91,
"group": "Advanced VLM & Multi-Modal Processing Tasks",
"question": "Can you generate precise bounding box coordinates [ymin, xmin, ymax, xmax] for all visible cracks?",
"explanation": "Provide normalized spatial coordinate outputs for downstream object detection models.",
"keywords": ["bounding box", "object detection", "spatial coordinates", "crack detection"],
"ai_action": "Output normalized bounding box arrays covering each detected crack segment."
},
{
"id": 92,
"group": "Advanced VLM & Multi-Modal Processing Tasks",
"question": "Can you segment the concrete block region and output a pixel-level binary mask of the crack network?",
"explanation": "Generate semantic segmentation masks to compute crack surface area percentage.",
"keywords": ["semantic segmentation", "binary mask", "pixel mask", "crack area"],
"ai_action": "Generate polygonal boundary coordinates defining the exact crack region mask."
},
{
"id": 93,
"group": "Advanced VLM & Multi-Modal Processing Tasks",
"question": "How does the crack width measured in this current photo compare to a previous baseline image?",
"explanation": "Perform temporal defect comparison to track degradation rate over time.",
"keywords": ["temporal comparison", "baseline tracking", "crack growth rate", "delta analysis"],
"ai_action": "Compare visual crack dimensions against baseline reference values."
},
{
"id": 94,
"group": "Advanced VLM & Multi-Modal Processing Tasks",
"question": "Can you categorize each identified defect into standardized inspection taxonomy codes (e.g., AASHTO / CoSF)?",
"explanation": "Standardize defect tagging for direct integration with asset management databases.",
"keywords": ["defect taxonomy", "AASHTO code", "inspection standard", "asset management"],
"ai_action": "Map visual features to industry-standard defect classification codes."
},
{
"id": 95,
"group": "Advanced VLM & Multi-Modal Processing Tasks",
"question": "Can you generate a natural language narrative describing the structural defect for an automated report?",
"explanation": "Produce formal technical prose for automated bridge condition report generation.",
"keywords": ["report generation", "technical narrative", "automated summary", "structural text"],
"ai_action": "Synthesize visual findings into a formal 3-sentence engineering report paragraph."
},
{
"id": 96,
"group": "Advanced VLM & Multi-Modal Processing Tasks",
"question": "What is the confidence score of the VLM model in identifying active corrosion versus surface dirt?",
"explanation": "Provide self-calibration confidence metrics to support reliable AI decision-making.",
"keywords": ["confidence score", "model certainty", "AI reliability", "classification score"],
"ai_action": "Evaluate visual clarity and feature distinction to output a confidence percentage."
},
{
"id": 97,
"group": "Advanced VLM & Multi-Modal Processing Tasks",
"question": "Can you estimate the 3D surface normal orientation of the cracked face relative to the camera lens?",
"explanation": "3D surface normal estimation enables accurate 3D reconstruction and depth mapping.",
"keywords": ["surface normal", "3D reconstruction", "depth estimation", "camera pose"],
"ai_action": "Calculate surface orientation vectors for the primary concrete face."
},
{
"id": 98,
"group": "Advanced VLM & Multi-Modal Processing Tasks",
"question": "Which visual features in this image contributed most to the AI's classification of 'Critical Damage'?",
"explanation": "Provide explainable AI (XAI) attention heatmaps highlighting key diagnostic regions.",
"keywords": ["explainable AI", "attention map", "visual rationale", "feature importance"],
"ai_action": "Highlight visual regions (crack intersection, spall boundary) driving high-severity ratings."
},
{
"id": 99,
"group": "Advanced VLM & Multi-Modal Processing Tasks",
"question": "Can you cross-reference visual features with ultrasound or non-destructive test (NDT) request triggers?",
"explanation": "Identify visual cues that necessitate deeper non-destructive internal testing.",
"keywords": ["NDT request", "ultrasound trigger", "non-destructive testing", "internal defect"],
"ai_action": "Flag complex surface crack networks as triggers for recommended ultrasonic testing."
},
{
"id": 100,
"group": "Advanced VLM & Multi-Modal Processing Tasks",
"question": "Is the resolution and dynamic range of this image sufficient for automated 3D mesh photogrammetry?",
"explanation": "Validate image quality metrics prior to attempting 3D photogrammetric reconstruction.",
"keywords": ["photogrammetry", "3D mesh", "image resolution", "quality audit"],
"ai_action": "Check image sharpness, exposure balance, and resolution against 3D modeling standards."
}
]