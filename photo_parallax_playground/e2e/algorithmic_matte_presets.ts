export type CompareHintPoint = {
  x: number;
  y: number;
};

export type CompareHintStroke = {
  mode: "closer" | "farther" | "protect" | "erase";
  size: number;
  points: CompareHintPoint[];
};

export type CompareGroupBox = {
  mode: "foreground-group" | "midground-group";
  x: number;
  y: number;
  width: number;
  height: number;
};

export type CompareMatteSeed = {
  mode: "add" | "subtract" | "protect";
  x: number;
  y: number;
};

export type AlgorithmicMattePreset = {
  sampleId: string;
  description: string;
  brushGroup: {
    hintStrokes: CompareHintStroke[];
    groupBoxes: CompareGroupBox[];
    note: string;
  };
  matte: {
    matteSettings?: {
      view?: "rgb" | "depth";
      visible?: boolean;
      growRadius?: number;
      edgeSnap?: number;
      opacity?: number;
    };
    matteSeeds: CompareMatteSeed[];
    note: string;
  };
};

export const ALGORITHMIC_MATTE_PRESETS: Record<string, AlgorithmicMattePreset> = {
  "cassette-closeup": {
    sampleId: "cassette-closeup",
    description: "Group both hands with the cassette instead of letting perspective split them apart.",
    brushGroup: {
      note: "Foreground lock around both hands and cassette with light protect hints around edges.",
      groupBoxes: [
        { mode: "foreground-group", x: 0.16, y: 0.21, width: 0.68, height: 0.63 },
      ],
      hintStrokes: [
        {
          mode: "closer",
          size: 0.038,
          points: [
            { x: 0.33, y: 0.58 },
            { x: 0.43, y: 0.54 },
            { x: 0.54, y: 0.52 },
            { x: 0.66, y: 0.49 },
          ],
        },
        {
          mode: "protect",
          size: 0.026,
          points: [
            { x: 0.22, y: 0.63 },
            { x: 0.29, y: 0.69 },
            { x: 0.74, y: 0.57 },
          ],
        },
      ],
    },
    matte: {
      note: "Grow from cassette and both hands, subtract lower background spill, protect left hand edge.",
      matteSettings: {
        visible: true,
        view: "rgb",
        growRadius: 0.18,
        edgeSnap: 0.11,
        opacity: 0.66,
      },
      matteSeeds: [
        { mode: "add", x: 0.34, y: 0.62 },
        { mode: "add", x: 0.49, y: 0.54 },
        { mode: "add", x: 0.66, y: 0.5 },
        { mode: "protect", x: 0.24, y: 0.7 },
        { mode: "subtract", x: 0.18, y: 0.88 },
        { mode: "subtract", x: 0.84, y: 0.83 },
      ],
    },
  },
  "keyboard-hands": {
    sampleId: "keyboard-hands",
    description: "Keep the keyboard and hands together as near plane instead of slicing them diagonally.",
    brushGroup: {
      note: "Foreground group across keyboard and hands, with closer stroke following keybed.",
      groupBoxes: [
        { mode: "foreground-group", x: 0.08, y: 0.43, width: 0.78, height: 0.39 },
        { mode: "midground-group", x: 0.62, y: 0.11, width: 0.26, height: 0.18 },
      ],
      hintStrokes: [
        {
          mode: "closer",
          size: 0.034,
          points: [
            { x: 0.18, y: 0.66 },
            { x: 0.32, y: 0.64 },
            { x: 0.47, y: 0.61 },
            { x: 0.62, y: 0.57 },
          ],
        },
        {
          mode: "protect",
          size: 0.022,
          points: [
            { x: 0.2, y: 0.54 },
            { x: 0.71, y: 0.52 },
          ],
        },
      ],
    },
    matte: {
      note: "Grow matte from both hands and keyboard center, cut back desk spill and protect fingertips.",
      matteSettings: {
        visible: true,
        view: "rgb",
        growRadius: 0.17,
        edgeSnap: 0.1,
        opacity: 0.7,
      },
      matteSeeds: [
        { mode: "add", x: 0.22, y: 0.59 },
        { mode: "add", x: 0.42, y: 0.63 },
        { mode: "add", x: 0.63, y: 0.57 },
        { mode: "protect", x: 0.18, y: 0.51 },
        { mode: "protect", x: 0.71, y: 0.5 },
        { mode: "subtract", x: 0.08, y: 0.9 },
        { mode: "subtract", x: 0.91, y: 0.85 },
      ],
    },
  },
  "hover-politsia": {
    sampleId: "hover-politsia",
    description: "Push the vehicle and nearby right-side action forward without grabbing the whole street.",
    brushGroup: {
      note: "Foreground box around hovercar, mild farther stroke into open street.",
      groupBoxes: [
        { mode: "foreground-group", x: 0.49, y: 0.33, width: 0.28, height: 0.24 },
        { mode: "midground-group", x: 0.07, y: 0.38, width: 0.3, height: 0.36 },
      ],
      hintStrokes: [
        {
          mode: "closer",
          size: 0.03,
          points: [
            { x: 0.56, y: 0.43 },
            { x: 0.63, y: 0.41 },
            { x: 0.7, y: 0.39 },
          ],
        },
        {
          mode: "farther",
          size: 0.032,
          points: [
            { x: 0.2, y: 0.62 },
            { x: 0.32, y: 0.59 },
            { x: 0.44, y: 0.56 },
          ],
        },
      ],
    },
    matte: {
      note: "Grow around hovercar body and windshield, subtract street and sky spill.",
      matteSettings: {
        visible: true,
        view: "rgb",
        growRadius: 0.15,
        edgeSnap: 0.095,
        opacity: 0.68,
      },
      matteSeeds: [
        { mode: "add", x: 0.59, y: 0.44 },
        { mode: "add", x: 0.67, y: 0.41 },
        { mode: "protect", x: 0.73, y: 0.38 },
        { mode: "subtract", x: 0.16, y: 0.66 },
        { mode: "subtract", x: 0.88, y: 0.18 },
      ],
    },
  },
  "drone-portrait": {
    sampleId: "drone-portrait",
    description: "Keep the portrait subject and binocular rig together as one foreground object.",
    brushGroup: {
      note: "Foreground lock across face, torso and binoculars, with protect hints on the shoulder edges.",
      groupBoxes: [
        { mode: "foreground-group", x: 0.17, y: 0.08, width: 0.64, height: 0.84 },
        { mode: "midground-group", x: 0.63, y: 0.16, width: 0.22, height: 0.18 },
      ],
      hintStrokes: [
        {
          mode: "closer",
          size: 0.034,
          points: [
            { x: 0.43, y: 0.18 },
            { x: 0.46, y: 0.34 },
            { x: 0.49, y: 0.51 },
            { x: 0.48, y: 0.7 },
          ],
        },
        {
          mode: "protect",
          size: 0.024,
          points: [
            { x: 0.26, y: 0.58 },
            { x: 0.73, y: 0.58 },
            { x: 0.51, y: 0.82 },
          ],
        },
      ],
    },
    matte: {
      note: "Grow from face, beard and binoculars, subtract outer bokeh background and protect jacket silhouette.",
      matteSettings: {
        visible: true,
        view: "rgb",
        growRadius: 0.19,
        edgeSnap: 0.11,
        opacity: 0.68,
      },
      matteSeeds: [
        { mode: "add", x: 0.46, y: 0.19 },
        { mode: "add", x: 0.48, y: 0.39 },
        { mode: "add", x: 0.44, y: 0.66 },
        { mode: "protect", x: 0.27, y: 0.58 },
        { mode: "protect", x: 0.72, y: 0.58 },
        { mode: "subtract", x: 0.08, y: 0.16 },
        { mode: "subtract", x: 0.91, y: 0.17 },
        { mode: "subtract", x: 0.9, y: 0.9 },
      ],
    },
  },
  "punk-rooftop": {
    sampleId: "punk-rooftop",
    description: "Keep the seated rooftop figure together instead of letting the city swallow the lower body.",
    brushGroup: {
      note: "Foreground lock around the seated figure with a mild protect pass around the leg silhouette.",
      groupBoxes: [
        { mode: "foreground-group", x: 0.06, y: 0.13, width: 0.47, height: 0.78 },
        { mode: "midground-group", x: 0.5, y: 0.15, width: 0.42, height: 0.52 },
      ],
      hintStrokes: [
        {
          mode: "closer",
          size: 0.036,
          points: [
            { x: 0.23, y: 0.22 },
            { x: 0.26, y: 0.39 },
            { x: 0.31, y: 0.58 },
            { x: 0.34, y: 0.73 },
          ],
        },
        {
          mode: "protect",
          size: 0.024,
          points: [
            { x: 0.11, y: 0.73 },
            { x: 0.39, y: 0.68 },
            { x: 0.34, y: 0.84 },
          ],
        },
      ],
    },
    matte: {
      note: "Grow from head, torso and knee, subtract skyline spill and protect the rooftop edge near the boots.",
      matteSettings: {
        visible: true,
        view: "rgb",
        growRadius: 0.18,
        edgeSnap: 0.1,
        opacity: 0.67,
      },
      matteSeeds: [
        { mode: "add", x: 0.24, y: 0.2 },
        { mode: "add", x: 0.24, y: 0.45 },
        { mode: "add", x: 0.33, y: 0.7 },
        { mode: "protect", x: 0.12, y: 0.76 },
        { mode: "protect", x: 0.38, y: 0.82 },
        { mode: "subtract", x: 0.71, y: 0.28 },
        { mode: "subtract", x: 0.92, y: 0.88 },
      ],
    },
  },
  "truck-driver": {
    sampleId: "truck-driver",
    description: "Keep the driver, hands and steering wheel together inside the cab frame.",
    brushGroup: {
      note: "Foreground lock around the driver and steering wheel, protect the cab window edges from overgrab.",
      groupBoxes: [
        { mode: "foreground-group", x: 0.27, y: 0.1, width: 0.54, height: 0.7 },
        { mode: "midground-group", x: 0.0, y: 0.0, width: 0.28, height: 0.84 },
      ],
      hintStrokes: [
        {
          mode: "closer",
          size: 0.034,
          points: [
            { x: 0.58, y: 0.22 },
            { x: 0.55, y: 0.39 },
            { x: 0.47, y: 0.57 },
          ],
        },
        {
          mode: "protect",
          size: 0.022,
          points: [
            { x: 0.16, y: 0.52 },
            { x: 0.82, y: 0.2 },
            { x: 0.87, y: 0.63 },
          ],
        },
      ],
    },
    matte: {
      note: "Grow from face, torso and steering wheel, subtract truck exterior and protect the right seat boundary.",
      matteSettings: {
        visible: true,
        view: "rgb",
        growRadius: 0.17,
        edgeSnap: 0.1,
        opacity: 0.68,
      },
      matteSeeds: [
        { mode: "add", x: 0.58, y: 0.23 },
        { mode: "add", x: 0.55, y: 0.47 },
        { mode: "add", x: 0.35, y: 0.54 },
        { mode: "protect", x: 0.82, y: 0.56 },
        { mode: "protect", x: 0.18, y: 0.55 },
        { mode: "subtract", x: 0.08, y: 0.2 },
        { mode: "subtract", x: 0.44, y: 0.04 },
      ],
    },
  },
};

export function getAlgorithmicMattePreset(sampleId: string) {
  return ALGORITHMIC_MATTE_PRESETS[sampleId] || ALGORITHMIC_MATTE_PRESETS["cassette-closeup"];
}

export const DEFAULT_COMPARE_SAMPLE_IDS = [
  "cassette-closeup",
  "keyboard-hands",
  "hover-politsia",
  "drone-portrait",
  "punk-rooftop",
  "truck-driver",
];
