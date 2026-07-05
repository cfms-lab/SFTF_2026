(* ::Package:: *)

ClearAll[
  triA, triB, mcenter, filamentCriticalAngle, angleTest,
  triangleArea, triangleNormal, rotationMatrix, rotateTriangle,
  supportVolume, combinedSupportVolume, supportSegments, supportVolumePrism,
  supportVolumeRegion, supportNeedsSupportQ, supportIntersectionRegion,
  supportIntersectionVolumeComponents, supportIntersectionVolume,
  supportNonVisibleIntersectionVolume, blackNumber,
  trianglePlaneFunction, supportPrismApproxInfo, triangleQuadraturePoints,
  approximateSupportIntersectionVolume, approximateVssGrid, approximateContourPlot,
  relativeErrorGrid, errorRateReport,
  coolWarmColorscale, coolWarmColor,
  yawValues, pitchValues, supportComponentGrid, vssGrid, vnvGrid, approxVssGrid,
  contourPlot, vnvContourPlot, approxContourPlot,
  errorStats, errorSummaryText, plotImageSize
];

triA = N[{{0.0, 0.0, 3.0}, {0.0, 1.0, 3.0}, {1.0, 0.0, 3.0}}];
triB = N[{{0, 0.0, 1.0}, {0, 1.0, 1.0}, {1, 0.0, 1.0}}];
mcenter = N[{0.0, 0.0, 2.0}];
filamentCriticalAngle = 60.0;
angleTest = 5.0;

triangleArea[tri_] := Norm[Cross[tri[[2]] - tri[[1]], tri[[3]] - tri[[1]]]]/2.0;

triangleNormal[tri_] := Normalize[Cross[tri[[2]] - tri[[1]], tri[[3]] - tri[[1]]]];

rotationMatrix[yawDeg_, pitchDeg_] := Module[
  {yaw = yawDeg Degree, pitch = pitchDeg Degree, rotX, rotY},
  rotX = {
    {1.0, 0.0, 0.0},
    {0.0, Cos[yaw], -Sin[yaw]},
    {0.0, Sin[yaw], Cos[yaw]}
  };
  rotY = {
    {Cos[pitch], 0.0, Sin[pitch]},
    {0.0, 1.0, 0.0},
    {-Sin[pitch], 0.0, Cos[pitch]}
  };
  rotY . rotX
];

rotateTriangle[tri_, center_, yawDeg_, pitchDeg_] := Module[
  {rot = rotationMatrix[yawDeg, pitchDeg]},
  (center + rot . (# - center)) & /@ tri
];

supportVolume[sourceTri_, targetTri_, yawDeg_, pitchDeg_, criticalAngleDeg_] := Module[
  {
    rotatedSource, rotatedTarget, verticalAxis, pairVector, depth,
    normalSource, areaSource, projectedAreaSource, supportDirection,
    supportAngle, needsSupport
  },
  rotatedSource = rotateTriangle[sourceTri, mcenter, yawDeg, pitchDeg];
  rotatedTarget = rotateTriangle[targetTri, mcenter, yawDeg, pitchDeg];
  verticalAxis = {0.0, 0.0, 1.0};
  pairVector = Mean[rotatedTarget] - Mean[rotatedSource];
  depth = Abs[verticalAxis . pairVector];
  normalSource = triangleNormal[rotatedSource];
  areaSource = triangleArea[rotatedSource];
  projectedAreaSource = areaSource Abs[verticalAxis . normalSource];
  supportDirection = If[verticalAxis . pairVector < 0.0, -verticalAxis, verticalAxis];
  supportAngle = ArcCos[Clip[Abs[normalSource . supportDirection], {0.0, 1.0}]]/Degree;
  needsSupport =
    criticalAngleDeg <= 0.0 ||
    (criticalAngleDeg < 90.0 && supportAngle >= criticalAngleDeg);
  If[needsSupport, depth projectedAreaSource, 0.0]
];

combinedSupportVolume[yawDeg_, pitchDeg_] :=
  supportVolume[triA, triB, yawDeg, pitchDeg, filamentCriticalAngle] +
  supportVolume[triB, triA, yawDeg, pitchDeg, filamentCriticalAngle];

supportSegments[sourceTri_, targetTri_, yawDeg_, pitchDeg_] := Module[
  {rotatedSource, rotatedTarget, verticalAxis, pairVector, deltaZ},
  rotatedSource = rotateTriangle[sourceTri, mcenter, yawDeg, pitchDeg];
  rotatedTarget = rotateTriangle[targetTri, mcenter, yawDeg, pitchDeg];
  verticalAxis = {0.0, 0.0, 1.0};
  pairVector = Mean[rotatedTarget] - Mean[rotatedSource];
  deltaZ = verticalAxis . pairVector;
  Line[{#, # + deltaZ verticalAxis}] & /@ rotatedSource
];

supportVolumePrism[sourceTri_, targetTri_, yawDeg_, pitchDeg_] := Module[
  {rotatedSource, rotatedTarget, verticalAxis, pairVector, deltaZ, top},
  rotatedSource = rotateTriangle[sourceTri, mcenter, yawDeg, pitchDeg];
  rotatedTarget = rotateTriangle[targetTri, mcenter, yawDeg, pitchDeg];
  verticalAxis = {0.0, 0.0, 1.0};
  pairVector = Mean[rotatedTarget] - Mean[rotatedSource];
  deltaZ = verticalAxis . pairVector;
  top = (# + deltaZ verticalAxis) & /@ rotatedSource;
  {
    Polygon[rotatedSource],
    Polygon[top],
    Polygon[{rotatedSource[[1]], rotatedSource[[2]], top[[2]], top[[1]]}],
    Polygon[{rotatedSource[[2]], rotatedSource[[3]], top[[3]], top[[2]]}],
    Polygon[{rotatedSource[[3]], rotatedSource[[1]], top[[1]], top[[3]]}]
  }
];

supportVolumeRegion[sourceTri_, targetTri_, yawDeg_, pitchDeg_] := Module[
  {rotatedSource, rotatedTarget, verticalAxis, pairVector, deltaZ, top},
  rotatedSource = rotateTriangle[sourceTri, mcenter, yawDeg, pitchDeg];
  rotatedTarget = rotateTriangle[targetTri, mcenter, yawDeg, pitchDeg];
  verticalAxis = {0.0, 0.0, 1.0};
  pairVector = Mean[rotatedTarget] - Mean[rotatedSource];
  deltaZ = verticalAxis . pairVector;
  top = (# + deltaZ verticalAxis) & /@ rotatedSource;
  ConvexHullMesh[Join[rotatedSource, top]]
];

supportNeedsSupportQ[sourceTri_, targetTri_, yawDeg_, pitchDeg_, criticalAngleDeg_: filamentCriticalAngle] := Module[
  {
    rotatedSource, rotatedTarget, verticalAxis, pairVector, supportDirection,
    normalSource, supportAngle
  },
  rotatedSource = rotateTriangle[sourceTri, mcenter, yawDeg, pitchDeg];
  rotatedTarget = rotateTriangle[targetTri, mcenter, yawDeg, pitchDeg];
  verticalAxis = {0.0, 0.0, 1.0};
  pairVector = Mean[rotatedTarget] - Mean[rotatedSource];
  supportDirection = If[verticalAxis . pairVector < 0.0, -verticalAxis, verticalAxis];
  normalSource = triangleNormal[rotatedSource];
  supportAngle = ArcCos[Clip[Abs[normalSource . supportDirection], {0.0, 1.0}]]/Degree;
  criticalAngleDeg <= 0.0 ||
    (criticalAngleDeg < 90.0 && supportAngle >= criticalAngleDeg)
];

supportIntersectionRegion[yawDeg_, pitchDeg_] := Quiet@Check[
  BoundaryDiscretizeRegion[
    RegionIntersection[
      supportVolumeRegion[triA, triB, yawDeg, pitchDeg],
      supportVolumeRegion[triB, triA, yawDeg, pitchDeg]
    ]
  ],
  EmptyRegion[3]
];

supportIntersectionVolumeComponents[
  yawDeg_, pitchDeg_,
  criticalAngleDeg_: filamentCriticalAngle
] := Module[
  {region, volume, isSupportSupport},
  region = Quiet@Check[
    RegionIntersection[
      supportVolumeRegion[triA, triB, yawDeg, pitchDeg],
      supportVolumeRegion[triB, triA, yawDeg, pitchDeg]
    ],
    EmptyRegion[3]
  ];
  volume = Quiet@Check[RegionMeasure[region], 0.0];
  isSupportSupport =
    volume > 10^-12 &&
    supportNeedsSupportQ[triA, triB, yawDeg, pitchDeg, criticalAngleDeg] &&
    supportNeedsSupportQ[triB, triA, yawDeg, pitchDeg, criticalAngleDeg];
  <|
    "v_ss" -> If[isSupportSupport, volume, 0.0],
    "v_nv" -> If[volume > 10^-12 && !isSupportSupport, volume, 0.0],
    "total" -> volume
  |>
];

supportIntersectionVolume[yawDeg_, pitchDeg_] :=
  supportIntersectionVolumeComponents[yawDeg, pitchDeg]["v_ss"];

supportNonVisibleIntersectionVolume[yawDeg_, pitchDeg_] :=
  supportIntersectionVolumeComponents[yawDeg, pitchDeg]["v_nv"];

trianglePlaneFunction[tri_] := Module[
  {normal, c},
  normal = Cross[tri[[2]] - tri[[1]], tri[[3]] - tri[[1]]];
  If[Abs[normal[[3]]] < 10^-12, Return[None]];
  c = normal . tri[[1]];
  Function[{x, y}, (c - normal[[1]] x - normal[[2]] y)/normal[[3]]]
];

supportPrismApproxInfo[sourceTri_, targetTri_, center_, yawDeg_, pitchDeg_, criticalAngleDeg_] := Module[
  {
    rotatedSource, rotatedTarget, verticalAxis, pairVector, deltaZ,
    normalSource, supportDirection, supportAngle, needsSupport, zFun
  },
  rotatedSource = rotateTriangle[sourceTri, center, yawDeg, pitchDeg];
  rotatedTarget = rotateTriangle[targetTri, center, yawDeg, pitchDeg];
  verticalAxis = {0.0, 0.0, 1.0};
  pairVector = Mean[rotatedTarget] - Mean[rotatedSource];
  deltaZ = verticalAxis . pairVector;
  normalSource = triangleNormal[rotatedSource];
  supportDirection = If[deltaZ < 0.0, -verticalAxis, verticalAxis];
  supportAngle = ArcCos[Clip[Abs[normalSource . supportDirection], {0.0, 1.0}]]/Degree;
  needsSupport =
    criticalAngleDeg <= 0.0 ||
    (criticalAngleDeg < 90.0 && supportAngle >= criticalAngleDeg);
  zFun = trianglePlaneFunction[rotatedSource];
  If[
    !needsSupport || zFun === None || Area[Triangle[rotatedSource[[All, {1, 2}]]]] < 10^-12,
    None,
    <|
      "XY" -> rotatedSource[[All, {1, 2}]],
      "ZFun" -> zFun,
      "DeltaZ" -> deltaZ
    |>
  ]
];

triangleQuadraturePoints[pts_] := Module[
  {area, barycentricWeights, quadratureWeights},
  area = Area[Triangle[pts]];
  barycentricWeights = {
    {2.0/3.0, 1.0/6.0, 1.0/6.0},
    {1.0/6.0, 2.0/3.0, 1.0/6.0},
    {1.0/6.0, 1.0/6.0, 2.0/3.0}
  };
  quadratureWeights = ConstantArray[area/3.0, 3];
  Transpose[{barycentricWeights . pts, quadratureWeights}]
];

Options[approximateSupportIntersectionVolume] = {
  "ApproximationOrder" -> 0,
  "CriticalAngle" -> filamentCriticalAngle
};

approximateSupportIntersectionVolume[
  yawDeg_, pitchDeg_,
  OptionsPattern[]
] := approximateSupportIntersectionVolume[
  yawDeg, pitchDeg, triA, triB, mcenter,
  "ApproximationOrder" -> OptionValue["ApproximationOrder"],
  "CriticalAngle" -> OptionValue["CriticalAngle"]
];

approximateSupportIntersectionVolume[
  yawDeg_, pitchDeg_,
  sourceTri_, targetTri_, center_,
  OptionsPattern[]
] := Module[
  {
    criticalAngleDeg = OptionValue["CriticalAngle"], order = OptionValue["ApproximationOrder"],
    infoAB, infoBA, intersection2D, mesh, meshCoords, meshCells, cellPointIds,
    sampleTriangles, overlapHeightAt, refineTriangle
  },
  infoAB = supportPrismApproxInfo[sourceTri, targetTri, center, yawDeg, pitchDeg, criticalAngleDeg];
  infoBA = supportPrismApproxInfo[targetTri, sourceTri, center, yawDeg, pitchDeg, criticalAngleDeg];
  If[infoAB === None || infoBA === None, Return[0.0]];

  intersection2D = Quiet@Check[
    RegionIntersection[Triangle[infoAB["XY"]], Triangle[infoBA["XY"]]],
    EmptyRegion[2]
  ];
  If[RegionMeasure[intersection2D] <= 10^-12, Return[0.0]];

  mesh = Quiet@Check[DiscretizeRegion[intersection2D, MaxCellMeasure -> Infinity], $Failed];
  If[mesh === $Failed || MeshCellCount[mesh, 2] == 0, Return[0.0]];
  meshCoords = MeshCoordinates[mesh];
  meshCells = MeshCells[mesh, 2];
  cellPointIds = meshCells /. Polygon[ids_] :> ids;
  sampleTriangles = Join @@ (
    If[
      Length[#] == 3,
      {meshCoords[[#]]},
      Table[meshCoords[[{#[[1]], #[[i]], #[[i + 1]]}]], {i, 2, Length[#] - 1}]
    ] & /@ cellPointIds
  );

  refineTriangle[pts_, 0] := {pts};
  refineTriangle[pts_, n_Integer?Positive] := Module[
    {a = pts[[1]], b = pts[[2]], c = pts[[3]], ab, bc, ca},
    ab = (a + b)/2.0;
    bc = (b + c)/2.0;
    ca = (c + a)/2.0;
    Join @@ (refineTriangle[#, n - 1] & /@ {{a, ab, ca}, {ab, b, bc}, {ca, bc, c}, {ab, bc, ca}})
  ];
  sampleTriangles = Join @@ (refineTriangle[#, Max[0, Round[order]]] & /@ sampleTriangles);

  overlapHeightAt[{x_, y_}] := Module[
    {zA0, zA1, zB0, zB1},
    zA0 = infoAB["ZFun"][x, y];
    zA1 = zA0 + infoAB["DeltaZ"];
    zB0 = infoBA["ZFun"][x, y];
    zB1 = zB0 + infoBA["DeltaZ"];
    Max[0.0, Min[Max[zA0, zA1], Max[zB0, zB1]] - Max[Min[zA0, zA1], Min[zB0, zB1]]]
  ];

  Total[
    (Total[(overlapHeightAt[#[[1]]] #[[2]]) & /@ triangleQuadraturePoints[#]]) & /@ sampleTriangles
  ]
];

Options[approximateVssGrid] = Options[approximateSupportIntersectionVolume];

approximateVssGrid[OptionsPattern[]] := approximateVssGrid[
  triA, triB, mcenter, yawValues, pitchValues,
  "ApproximationOrder" -> OptionValue["ApproximationOrder"],
  "CriticalAngle" -> OptionValue["CriticalAngle"]
];

approximateVssGrid[
  sourceTri_, targetTri_, center_, yaws_, pitches_,
  OptionsPattern[]
] := Table[
  approximateSupportIntersectionVolume[
    yaw, pitch, sourceTri, targetTri, center,
    "ApproximationOrder" -> OptionValue["ApproximationOrder"],
    "CriticalAngle" -> OptionValue["CriticalAngle"]
  ],
  {pitch, pitches},
  {yaw, yaws}
];

Options[approximateContourPlot] = Join[
  Options[approximateSupportIntersectionVolume],
  {"Contours" -> 15, "ImageSize" :> plotImageSize}
];

approximateContourPlot[OptionsPattern[]] := approximateContourPlot[
  triA, triB, mcenter, yawValues, pitchValues,
  "ApproximationOrder" -> OptionValue["ApproximationOrder"],
  "CriticalAngle" -> OptionValue["CriticalAngle"],
  "Contours" -> OptionValue["Contours"],
  "ImageSize" -> OptionValue["ImageSize"]
];

approximateContourPlot[
  sourceTri_, targetTri_, center_, yaws_, pitches_,
  OptionsPattern[]
] := Module[
  {grid},
  grid = approximateVssGrid[
    sourceTri, targetTri, center, yaws, pitches,
    "ApproximationOrder" -> OptionValue["ApproximationOrder"],
    "CriticalAngle" -> OptionValue["CriticalAngle"]
  ];
  ListContourPlot[
    grid,
    DataRange -> {{Min[yaws], Max[yaws]}, {Min[pitches], Max[pitches]}},
    FrameLabel -> Style[#, Black] & /@ {"Yaw angle (deg)", "Pitch angle (deg)"},
    PlotLabel -> Style["Approx overlap support volume v_ss: triA <-> triB", Black],
    ColorFunction -> coolWarmColor,
    ColorFunctionScaling -> True,
    Contours -> OptionValue["Contours"],
    LabelStyle -> Black,
    PlotLegends -> Automatic,
    ImageSize -> OptionValue["ImageSize"]
  ]
];

relativeErrorGrid[exactGrid_, approximateGrid_, eps_: 10^-12] := MapThread[
  If[Abs[#1] <= eps && Abs[#2] <= eps, 0.0, Abs[#2 - #1]/Max[Abs[#1], eps]] &,
  {exactGrid, approximateGrid},
  2
];

errorRateReport[exactGrid_, approximateGrid_, eps_: 10^-12] := Module[
  {absError, relError, nonzeroRelError},
  absError = Abs[approximateGrid - exactGrid];
  relError = relativeErrorGrid[exactGrid, approximateGrid, eps];
  nonzeroRelError = Pick[Flatten[relError], Unitize[Flatten[Abs[exactGrid]]], 1];
  <|
    "MaxAbsoluteError" -> Max[absError],
    "MeanAbsoluteError" -> Mean[Flatten[absError]],
    "MaxRelativeErrorPercent" -> 100.0 Max[relError],
    "MeanRelativeErrorPercent" -> 100.0 Mean[Flatten[relError]],
    "MeanRelativeErrorPercentNonzeroExact" -> If[Length[nonzeroRelError] == 0, 0.0, 100.0 Mean[nonzeroRelError]]
  |>
];

blackNumber[value_, spec_] := Style[NumberForm[value, spec], Black];

coolWarmColorscale = {
  {0.0, RGBColor["#3b4cc0"]},
  {0.1, RGBColor["#5977e3"]},
  {0.2, RGBColor["#7b9ff9"]},
  {0.3, RGBColor["#9ebeff"]},
  {0.4, RGBColor["#c0d4f5"]},
  {0.5, RGBColor["#dddcdc"]},
  {0.6, RGBColor["#f2cbb7"]},
  {0.7, RGBColor["#f7aa8c"]},
  {0.8, RGBColor["#ee8468"]},
  {0.9, RGBColor["#d65244"]},
  {1.0, RGBColor["#b40426"]}
};

coolWarmColor[z_] := Blend[coolWarmColorscale, z];

yawValues = Range[0.0, 360.0, angleTest];
pitchValues = Range[0.0, 360.0, angleTest];
plotImageSize = 288;

supportComponentGrid = Table[
  supportIntersectionVolumeComponents[yaw, pitch],
  {pitch, pitchValues},
  {yaw, yawValues}
];

vssGrid = Map[#["v_ss"] &, supportComponentGrid, {2}];
vnvGrid = Map[#["v_nv"] &, supportComponentGrid, {2}];

approxVssGrid = approximateVssGrid[
  triA, triB, mcenter, yawValues, pitchValues,
  "ApproximationOrder" -> 0,
  "CriticalAngle" -> filamentCriticalAngle
];

errorStats = errorRateReport[vssGrid, approxVssGrid];

errorSummaryText = Style[
  Row[{
    "approx error: max abs=", blackNumber[errorStats["MaxAbsoluteError"], {8, 5}],
    ", mean abs=", blackNumber[errorStats["MeanAbsoluteError"], {8, 5}],
    ", max rel=", blackNumber[errorStats["MaxRelativeErrorPercent"], {7, 3}], "%",
    ", mean rel=", blackNumber[errorStats["MeanRelativeErrorPercent"], {7, 3}], "%",
    ", mean rel (nonzero exact)=",
    blackNumber[errorStats["MeanRelativeErrorPercentNonzeroExact"], {7, 3}], "%"
  }],
  Black
];

Print[errorSummaryText];

contourPlot = ListContourPlot[
  vssGrid,
  DataRange -> {{Min[yawValues], Max[yawValues]}, {Min[pitchValues], Max[pitchValues]}},
  FrameLabel -> Style[#, Black] & /@ {"Yaw angle (deg)", "Pitch angle (deg)"},
  PlotLabel -> Style["Overlap support volume v_ss: triA <-> triB", Black],
  ColorFunction -> coolWarmColor,
  ColorFunctionScaling -> True,
  Contours -> 15,
  LabelStyle -> Black,
  PlotLegends -> Automatic,
  ImageSize -> plotImageSize
];

vnvContourPlot = ListContourPlot[
  vnvGrid,
  DataRange -> {{Min[yawValues], Max[yawValues]}, {Min[pitchValues], Max[pitchValues]}},
  FrameLabel -> Style[#, Black] & /@ {"Yaw angle (deg)", "Pitch angle (deg)"},
  PlotLabel -> Style["Overlap support volume v_nv: triA <-> triB", Black],
  ColorFunction -> coolWarmColor,
  ColorFunctionScaling -> True,
  Contours -> 15,
  LabelStyle -> Black,
  PlotLegends -> Automatic,
  ImageSize -> plotImageSize
];

approxContourPlot = ListContourPlot[
  approxVssGrid,
  DataRange -> {{Min[yawValues], Max[yawValues]}, {Min[pitchValues], Max[pitchValues]}} ,
  FrameLabel -> Style[#, Black] & /@ {"Yaw angle (deg)", "Pitch angle (deg)"},
  PlotLabel -> Style["Approx overlap support volume v_ss", Black],
  ColorFunction -> coolWarmColor,
  ColorFunctionScaling -> True,
  Contours -> 15,
  LabelStyle -> Black,
  PlotLegends -> Automatic,
  ImageSize -> plotImageSize
];

Manipulate[
  Module[
    {
      rotatedA = rotateTriangle[triA, mcenter, yaw, pitch],
      rotatedB = rotateTriangle[triB, mcenter, yaw, pitch],
      vssAB = supportVolume[triA, triB, yaw, pitch, filamentCriticalAngle],
      vssBA = supportVolume[triB, triA, yaw, pitch, filamentCriticalAngle],
      candidateSum = combinedSupportVolume[yaw, pitch],
      intersectionRegion = supportIntersectionRegion[yaw, pitch],
      intersectionComponents = supportIntersectionVolumeComponents[yaw, pitch],
      vss, vnv, overlapKind,
      nearestYaw, nearestPitch
    },
    vss = intersectionComponents["v_ss"];
    vnv = intersectionComponents["v_nv"];
    overlapKind = If[vss > 10^-12, "v_ss", If[vnv > 10^-12, "v_nv", "none"]];
    nearestYaw = First@Nearest[yawValues -> yawValues, yaw];
    nearestPitch = First@Nearest[pitchValues -> pitchValues, pitch];
    Grid[
      {
        {
          Show[
            Graphics3D[
              {
                Opacity[0.28], Darker[Green], supportVolumePrism[triA, triB, yaw, pitch],
                Opacity[0.28], Purple, supportVolumePrism[triB, triA, yaw, pitch],
                Opacity[0.76], If[vss > 10^-12, Yellow, Orange], Specularity[White, 20], intersectionRegion,
                Opacity[0.68], Red, Polygon[rotatedA],
                Opacity[0.68], Blue, Polygon[rotatedB],
                Black, PointSize[Large], Point[mcenter],
                Thick, Darker[Green], supportSegments[triA, triB, yaw, pitch],
                Thick, Purple, supportSegments[triB, triA, yaw, pitch]
              },
              Boxed -> True,
              Axes -> True,
              AxesLabel -> {"x", "y", "z"},
              PlotRange -> {{-2.2, 2.2}, {-2.2, 2.2}, {-0.5, 4.5}},
              ImageSize -> plotImageSize
            ],
            PlotLabel -> Style[
              Row[{
                "yaw=", blackNumber[yaw, {5, 1}],
                ", pitch=", blackNumber[pitch, {5, 1}],
                ", overlap ", overlapKind,
                "=", blackNumber[vss + vnv, {8, 5}]
              }],
              Black
            ]
          ],
          Column[
            {
              Framed[
                Grid[
                  {
                    {Style["triA -> triB candidate", Black], blackNumber[vssAB, {8, 5}]},
                    {Style["triB -> triA candidate", Black], blackNumber[vssBA, {8, 5}]},
                    {Style["candidate sum", Black], blackNumber[candidateSum, {8, 5}]},
                    {Style["v_ss overlap", Black, Bold], Style[blackNumber[vss, {8, 5}], 18, Bold, Black]},
                    {Style["v_nv overlap", Black, Bold], Style[blackNumber[vnv, {8, 5}], 18, Bold, Black]},
                    {Style["overlap class", Black], Style[overlapKind, Black]},
                    {Style["region color", Black], Style["yellow=v_ss, orange=v_nv", Black]}
                  },
                  Alignment -> Left,
                  Spacings -> {2, 1}
                ],
                Background -> Lighter[Gray, 0.92],
                FrameStyle -> GrayLevel[0.7],
                RoundingRadius -> 4
              ],
              Show[
                contourPlot,
                Epilog -> {
                  Black, PointSize[Large], Point[{nearestYaw, nearestPitch}],
                  White, PointSize[Medium], Point[{nearestYaw, nearestPitch}]
                }
              ],
              Show[
                vnvContourPlot,
                Epilog -> {
                  Black, PointSize[Large], Point[{nearestYaw, nearestPitch}],
                  White, PointSize[Medium], Point[{nearestYaw, nearestPitch}]
                }
              ],
              Show[
                approxContourPlot,
                Epilog -> {
                  Black, PointSize[Large], Point[{nearestYaw, nearestPitch}],
                  White, PointSize[Medium], Point[{nearestYaw, nearestPitch}]
                }
              ],
              errorSummaryText
            }
          ]
        }
      }
    ]
  ],
  {{yaw, 0.0, "yaw (deg)"}, 0.0, 360.0, angleTest, Appearance -> "Labeled"},
  {{pitch, 0.0, "pitch (deg)"}, 0.0, 360.0, angleTest, Appearance -> "Labeled"},
  LabelStyle -> Black,
  TrackedSymbols :> {yaw, pitch}
]



