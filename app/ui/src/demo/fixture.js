// Labeled demo fixture — exercises the review surface with no backend.
// NOT inspection data: the canvas draws a procedural schematic (see
// MaskOverlay) and this JSON only demonstrates rendering + interaction.

export const DEMO_NOTE = 'Crack near top edge, seepage observed';

export const DEMO_RESULT = {
  request_id: 'req_demo000000000000000001',
  asset_id: 'DEMO-DRAIN-001',
  asset_type: 'drainage_structure',
  model_trace: {
    sam: 'sam-3.1',
    vision: 'llama-4-maverick-17b-128e-vision',
    vision_fallback_used: false,
    reasoning: 'muse-spark-1.3',
    planning: 'muse-wonder',
    timestamp: '2026-10-26T00:00:00+00:00',
  },
  segmentations: [
    {
      mask_id: 'mask_1',
      label: 'crack',
      bbox: [120, 80, 340, 150],
      confidence: 0.87,
      rle: { size: [8, 8], counts: [2, 2, 6, 2, 6, 2, 6, 2, 6, 2, 6, 2, 6, 2, 6, 2, 4] },
      source_image: 'image_0',
    },
  ],
  observations: [
    {
      text: 'Linear crack near top edge with active seepage',
      evidence: [
        { source: 'image_0', mask_id: 'mask_1', span: null },
        { source: 'maintenance_note', mask_id: null, span: [0, 20] },
      ],
      uncertainty: 0.35,
    },
  ],
  discrepancies: ['Note estimates length but no scale reference is visible'],
  missing_information: ['crack_dimensions', 'inspection_date'],
  recommended_next_step: 'Request qualified inspection with measurement tape.',
  human_review_required: true,
  cost_cents: 11.0,
  cost_priced: false,
};

// Schematic canvas size used when no real image is loaded.
export const DEMO_IMAGE = { width: 480, height: 270 };
