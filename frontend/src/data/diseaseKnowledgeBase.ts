/**
 * Curated 15-Class PlantVillage Agronomic Knowledge Base
 * Preserves domain knowledge from src/dashboard.py with strict provenance separation:
 * - Classification output = PREDICTED
 * - Agronomic treatment protocol = RECOMMENDED
 */

export interface DiseaseKnowledgeEntry {
  className: string;
  displayName: string;
  scientificName: string;
  crop: 'Bell Pepper' | 'Potato' | 'Tomato';
  severity: 'None' | 'Moderate' | 'High' | 'Critical';
  statusTag: string;
  overview: string;
  treatments: string[];
}

export const DISEASE_KNOWLEDGE_BASE: Record<string, DiseaseKnowledgeEntry> = {
  Pepper__bell___Bacterial_spot: {
    className: 'Pepper__bell___Bacterial_spot',
    displayName: 'Bell Pepper — Bacterial Spot',
    scientificName: 'Xanthomonas campestris pv. vesicatoria',
    crop: 'Bell Pepper',
    severity: 'High',
    statusTag: 'CRITICAL RISK',
    overview: 'Bacterial leaf spots that cause premature defoliation and severe fruit blistering.',
    treatments: [
      'Apply preventive copper-based bactericides combined with mancozeb early in the season.',
      'Avoid overhead sprinkler irrigation; switch to drip irrigation to keep foliage dry.',
      'Sanitize pruning tools with a 10% bleach solution between crop rows.',
      'Destroy or deeply bury heavily infected crop residue after harvest.',
    ],
  },
  Pepper__bell___healthy: {
    className: 'Pepper__bell___healthy',
    displayName: 'Bell Pepper — Healthy Plant',
    scientificName: 'Capsicum annuum',
    crop: 'Bell Pepper',
    severity: 'None',
    statusTag: 'OPTIMAL HEALTH',
    overview: 'Vibrant foliage with balanced chlorophyll density and no active pathogen signs.',
    treatments: [
      'Maintain consistent soil moisture and well-balanced N-P-K fertilization.',
      'Conduct routine weekly scouting under leaf canopies for early aphid or thrip activity.',
      'Ensure proper spacing for optimal canopy airflow and sunlight penetration.',
    ],
  },
  Potato___Early_blight: {
    className: 'Potato___Early_blight',
    displayName: 'Potato — Early Blight',
    scientificName: 'Alternaria solani',
    crop: 'Potato',
    severity: 'Moderate',
    statusTag: 'ACTION REQUIRED',
    overview: "Concentric ring 'target' lesions primarily attacking older foliage near the soil line.",
    treatments: [
      'Apply protectant fungicides (chlorothalonil or azoxystrobin) at first lesion detection.',
      'Prune and remove infected lower foliage touching the soil line.',
      'Practice a 3-year crop rotation with non-solanaceous crops (cereals, legumes).',
    ],
  },
  Potato___Late_blight: {
    className: 'Potato___Late_blight',
    displayName: 'Potato — Late Blight',
    scientificName: 'Phytophthora infestans',
    crop: 'Potato',
    severity: 'Critical',
    statusTag: 'HIGH SEVERITY ALERT',
    overview: 'Rapidly spreading water-soaked dark lesions with white sporulation on leaf undersides in humid weather.',
    treatments: [
      'Emergency intervention: apply systemic oomycete fungicides (mefenoxam, cymoxanil, or mandipropamid).',
      'Immediately destroy cull piles and rogue out infected volunteer potato plants.',
      'Hill tubers thoroughly to prevent rain from washing spores onto developing tubers.',
      'Avoid harvesting during wet conditions; desiccate vines 2 weeks prior to harvest.',
    ],
  },
  Potato___healthy: {
    className: 'Potato___healthy',
    displayName: 'Potato — Healthy Plant',
    scientificName: 'Solanum tuberosum',
    crop: 'Potato',
    severity: 'None',
    statusTag: 'OPTIMAL HEALTH',
    overview: 'Uniform green leaf tissue with strong vigor and zero necrotic symptoms.',
    treatments: [
      'Maintain regular hilling and uniform soil moisture to support tuber initiation.',
      'Apply balanced potassium to promote natural cell-wall resistance.',
      'Continue periodic leaf-underside inspections following cool rain events.',
    ],
  },
  Tomato_Bacterial_spot: {
    className: 'Tomato_Bacterial_spot',
    displayName: 'Tomato — Bacterial Spot',
    scientificName: 'Xanthomonas vesicatoria',
    crop: 'Tomato',
    severity: 'High',
    statusTag: 'ACTION REQUIRED',
    overview: 'Small, dark, greasy circular lesions on leaves and scab-like spots on tomato fruit.',
    treatments: [
      'Apply copper-mancozeb sprays every 7–10 days under warm, humid conditions.',
      'Never cultivate, prune, or harvest while tomato foliage is wet with dew or rain.',
      'Use certified pathogen-free seed stocks and resistant cultivars.',
    ],
  },
  Tomato_Early_blight: {
    className: 'Tomato_Early_blight',
    displayName: 'Tomato — Early Blight',
    scientificName: 'Alternaria linariae',
    crop: 'Tomato',
    severity: 'Moderate',
    statusTag: 'ACTION REQUIRED',
    overview: 'Bullseye target-pattern brown spots with surrounding yellow chlorotic halos on lower leaves.',
    treatments: [
      'Prune lowest leaves to maintain a 30 cm clear airflow zone above the soil surface.',
      'Apply organic bio-fungicides (Bacillus subtilis) or copper hydroxide sprays.',
      'Apply organic mulch to prevent soil-borne spores from splashing onto lower leaves.',
    ],
  },
  Tomato_Late_blight: {
    className: 'Tomato_Late_blight',
    displayName: 'Tomato — Late Blight',
    scientificName: 'Phytophthora infestans',
    crop: 'Tomato',
    severity: 'Critical',
    statusTag: 'HIGH SEVERITY ALERT',
    overview: 'Devastating water-soaked lesions that cause leaves, stems, and green fruit to collapse rapidly.',
    treatments: [
      'Apply targeted oomycete fungicides (dimethomorph, fluopicolide, or cyazofamid).',
      'Bag and remove severely infected plants on a dry day; do not compost infected tissue.',
      'Ensure wide row spacing (60–90 cm) for rapid canopy drying.',
    ],
  },
  Tomato_Leaf_Mold: {
    className: 'Tomato_Leaf_Mold',
    displayName: 'Tomato — Leaf Mold',
    scientificName: 'Passalora fulva',
    crop: 'Tomato',
    severity: 'Moderate',
    statusTag: 'MONITOR CLOSELY',
    overview: 'Pale green/yellow spots on upper leaf surfaces with olive-green velvety mold underneath.',
    treatments: [
      'Increase greenhouse or tunnel ventilation to keep relative humidity below 85%.',
      'Use horizontal airflow fans to eliminate damp microclimates.',
      'Apply copper fungicide or sulfur sprays if humidity cannot be lowered.',
    ],
  },
  Tomato_Septoria_leaf_spot: {
    className: 'Tomato_Septoria_leaf_spot',
    displayName: 'Tomato — Septoria Leaf Spot',
    scientificName: 'Septoria lycopersici',
    crop: 'Tomato',
    severity: 'Moderate',
    statusTag: 'ACTION REQUIRED',
    overview: 'Numerous small circular spots with grayish-white centers and dark brown borders.',
    treatments: [
      'Remove affected lower leaves as soon as initial spots appear.',
      'Apply chlorothalonil or copper protectant sprays at 7-day intervals.',
      'Stake or trellis plants to keep foliage off the ground.',
    ],
  },
  Tomato_Spider_mites_Two_spotted_spider_mite: {
    className: 'Tomato_Spider_mites_Two_spotted_spider_mite',
    displayName: 'Tomato — Two-Spotted Spider Mites',
    scientificName: 'Tetranychus urticae',
    crop: 'Tomato',
    severity: 'Moderate',
    statusTag: 'PEST MANAGEMENT',
    overview: 'Fine yellow stippling on foliage accompanied by delicate silky webbing under leaves.',
    treatments: [
      'Introduce beneficial predatory mites (Phytoseiulus persimilis).',
      'Spray insecticidal soap or neem oil targeting leaf undersides.',
      'Avoid excessive nitrogen fertilization, which accelerates mite reproduction.',
    ],
  },
  Tomato__Target_Spot: {
    className: 'Tomato__Target_Spot',
    displayName: 'Tomato — Target Spot',
    scientificName: 'Corynespora cassiicola',
    crop: 'Tomato',
    severity: 'Moderate',
    statusTag: 'ACTION REQUIRED',
    overview: 'Brown zonate lesions with light brown centers causing canopy blight in humid conditions.',
    treatments: [
      'Apply strobilurin or carboxamide fungicides following resistance-management rotations.',
      'Prune suckers to improve light penetration and wind airflow.',
      'Eliminate weeds and alternative solanaceous hosts around plot perimeters.',
    ],
  },
  Tomato__Tomato_YellowLeaf__Curl_Virus: {
    className: 'Tomato__Tomato_YellowLeaf__Curl_Virus',
    displayName: 'Tomato — Yellow Leaf Curl Virus (TYLCV)',
    scientificName: 'Begomovirus (Whitefly-transmitted)',
    crop: 'Tomato',
    severity: 'Critical',
    statusTag: 'VIRAL VECTOR ALERT',
    overview: 'Upward leaf cupping, severe internode stunting, chlorotic margins, and flower abortion.',
    treatments: [
      'Control silverleaf whitefly vectors (Bemisia tabaci) with yellow sticky traps and targeted insecticides.',
      'Install 50-mesh insect exclusion netting in high tunnels and nurseries.',
      'Rogue and destroy infected plants early—viral infections cannot be cured chemically.',
      'Plant TYLCV-resistant hybrids in subsequent seasons.',
    ],
  },
  Tomato__Tomato_mosaic_virus: {
    className: 'Tomato__Tomato_mosaic_virus',
    displayName: 'Tomato — Tomato Mosaic Virus (ToMV)',
    scientificName: 'Tobamovirus',
    crop: 'Tomato',
    severity: 'High',
    statusTag: 'VIRAL INFECTION',
    overview: 'Mottled light and dark green mosaic patterns with fern-like leaf distortion.',
    treatments: [
      'Disinfect pruning tools in 20% trisodium phosphate (TSP) or household bleach solution.',
      'Prohibit tobacco handling near tomato plots to prevent mechanical sap transmission.',
      'Remove and destroy symptomatic plants promptly.',
    ],
  },
  Tomato_healthy: {
    className: 'Tomato_healthy',
    displayName: 'Tomato — Healthy Plant',
    scientificName: 'Solanum lycopersicum',
    crop: 'Tomato',
    severity: 'None',
    statusTag: 'OPTIMAL HEALTH',
    overview: 'Rich emerald foliage with vigorous cell structure, balanced venation, and zero lesions.',
    treatments: [
      'Maintain deep, infrequent drip irrigation to encourage strong root development.',
      'Provide balanced calcium and magnesium nutrition to prevent blossom-end rot.',
      'Continue routine twice-weekly IPM canopy scouting.',
    ],
  },
};

export function getDiseaseKnowledge(className: string): DiseaseKnowledgeEntry {
  return (
    DISEASE_KNOWLEDGE_BASE[className] || {
      className,
      displayName: className.replace(/_+/g, ' ').trim(),
      scientificName: 'Unlisted Pathogen / Condition',
      crop: 'Tomato',
      severity: 'Moderate',
      statusTag: 'CLASSIFIED',
      overview: 'Pathology classification completed by ResNet-50 model.',
      treatments: ['Consult a certified local agronomist for cultivar-specific intervention protocols.'],
    }
  );
}
