ClearAll[
  loadTriPairShadowCore, randomUnitVector, randomOrthonormalFrame,
  randomVisibleTrianglePair, pairRegressionFeatures, angleRegressionFeatures,
  triPairShadowRegressionFeatures, numericSupportComponentValues,
  trainTriPairShadowRegression, triPairShadowRegressionPrediction,
  triPairShadowRegressionFunction, regressionTriPairShadowGrid, regressionTriPairShadowContour,
  triPairShadowRegressionDemo, showTriPairShadowRegressionDemo
];

loadTriPairShadowCore[] := Module[
  {baseDir, path, text, prefixEnd},
  If[ValueQ[approximateSupportIntersectionVolume], Return[Null]];
  baseDir = If[StringQ[$InputFileName] && $InputFileName =!= "", DirectoryName[$InputFileName], Directory[]];
  path = FileNameJoin[{baseDir, "[function]tri_pair_shadow.wl"}];
  If[!FileExistsQ[path], path = FileNameJoin[{Directory[], "[function]tri_pair_shadow.wl"}]];
  text = Import[path, "Text"];
  prefixEnd = First@First@StringPosition[text, "\nblackNumber"];
  ToExpression[StringTake[text, prefixEnd - 1]];
];

randomUnitVector[] := Normalize[RandomVariate[NormalDistribution[0, 1], 3]];

randomOrthonormalFrame[] := Module[
  {n, helper, u, v},
  n = randomUnitVector[];
  helper = If[Abs[n.{0.0, 0.0, 1.0}] < 0.9, {0.0, 0.0, 1.0}, {0.0, 1.0, 0.0}];
  u = Normalize[Cross[n, helper]];
  v = Normalize[Cross[n, u]];
  {u, v, n}
];

randomVisibleTrianglePair[] := Module[
  {u, v, n, centerA, gap, scaleA, scaleB, localA, localB, triA, triB, center},
  {u, v, n} = randomOrthonormalFrame[];
  centerA = RandomReal[{-0.25, 0.25}, 3];
  gap = RandomReal[{0.5, 2.5}];
  scaleA = RandomReal[{0.35, 1.2}];
  scaleB = RandomReal[{0.35, 1.2}];
  localA = scaleA {{0.0, 0.0}, {1.0, 0.0}, {0.15, 0.85}};
  localB = scaleB ({{0.0, 0.0}, {1.0, 0.0}, {0.15, 0.85}} + RandomReal[{-0.2, 0.2}, {3, 2}]);
  triA = centerA + (#1 u + #2 v & @@@ localA);
  triB = centerA - gap n + (#1 u + #2 v & @@@ Reverse[localB]);
  center = Mean[Join[triA, triB]];
  <|"triA" -> N[triA], "triB" -> N[triB], "mcenter" -> N[center]|>
];

pairRegressionFeatures[triA_, triB_, center_] := Module[
  {normalA, normalB, areaA, areaB, cA, cB, delta, dist, dir, vertical = {0.0, 0.0, 1.0}},
  normalA = triangleNormal[triA];
  normalB = triangleNormal[triB];
  areaA = triangleArea[triA];
  areaB = triangleArea[triB];
  cA = Mean[triA];
  cB = Mean[triB];
  delta = cB - cA;
  dist = Max[Norm[delta], 10^-12];
  dir = delta/dist;
  {
    areaA, areaB, Sqrt[areaA areaB], dist,
    normalA.normalB, Abs[normalA.vertical], Abs[normalB.vertical],
    dir.vertical, Abs[dir.vertical],
    normalA.dir, normalB.dir,
    Norm[cA - center], Norm[cB - center]
  }
];

angleRegressionFeatures[yaw_, pitch_] := Module[
  {y = yaw Degree, p = pitch Degree},
  {
    Sin[y], Cos[y], Sin[2 y], Cos[2 y],
    Sin[p], Cos[p], Sin[2 p], Cos[2 p],
    Sin[y] Sin[p], Cos[y] Sin[p], Sin[y] Cos[p], Cos[y] Cos[p],
    Sin[2 y] Cos[p], Cos[2 y] Cos[p]
  }
];

triPairShadowRegressionFeatures[triA_, triB_, center_, yaw_, pitch_] := Join[
  pairRegressionFeatures[triA, triB, center],
  angleRegressionFeatures[yaw, pitch]
];

numericSupportComponentValues[localTriA_, localTriB_, center_, yaw_, pitch_, criticalAngle_] := Module[
  {components, clean},
  components = Quiet@Check[
    Block[
      {triA = localTriA, triB = localTriB, mcenter = center},
      N@supportIntersectionVolumeComponents[yaw, pitch, criticalAngle]
    ],
    <|"v_ss" -> Indeterminate, "v_nv" -> Indeterminate, "total" -> Indeterminate|>
  ];
  clean[value_] := If[NumericQ[value] && value >= 0.0, value, 0.0];
  <|
    "v_ss" -> clean[components["v_ss"]],
    "v_nv" -> clean[components["v_nv"]],
    "total" -> clean[components["total"]]
  |>
];

Options[trainTriPairShadowRegression] = {
  "PairCount" -> 100,
  "OrientationSamples" -> 60,
  "YawRange" -> {0.0, 360.0},
  "PitchRange" -> {0.0, 360.0},
  "CriticalAngle" -> 60.0,
  "RandomSeed" -> 20260619,
  "Method" -> "LinearRegression",
  "TargetComponents" -> {"v_ss", "v_nv"}
};

trainTriPairShadowRegression[OptionsPattern[]] := Module[
  {
    pairCount = OptionValue["PairCount"], sampleCount = OptionValue["OrientationSamples"],
    yawRange = OptionValue["YawRange"], pitchRange = OptionValue["PitchRange"],
    criticalAngle = OptionValue["CriticalAngle"], seed = OptionValue["RandomSeed"],
    method = OptionValue["Method"], targetComponents = OptionValue["TargetComponents"],
    pairs, samples, pair, yaw, pitch, features, values, examplesByComponent,
    componentPredictors, predictor, elapsed
  },
  loadTriPairShadowCore[];
  targetComponents = If[ListQ[targetComponents], targetComponents, {targetComponents}];
  targetComponents = Select[DeleteDuplicates[targetComponents], MemberQ[{"v_ss", "v_nv"}, #] &];
  If[targetComponents === {}, targetComponents = {"v_ss", "v_nv"}];
  SeedRandom[seed];
  elapsed = AbsoluteTiming[
    pairs = Table[randomVisibleTrianglePair[], {pairCount}];
    samples = Flatten[
      Table[
        pair = pairs[[pairId]];
        Table[
          yaw = RandomReal[yawRange];
          pitch = RandomReal[pitchRange];
          features = triPairShadowRegressionFeatures[pair["triA"], pair["triB"], pair["mcenter"], yaw, pitch];
          values = numericSupportComponentValues[
            pair["triA"], pair["triB"], pair["mcenter"], yaw, pitch,
            criticalAngle
          ];
          <|"Features" -> features, "Values" -> values|>,
          {sampleCount}
        ],
        {pairId, pairCount}
      ],
      1
    ];
    examplesByComponent = AssociationMap[
      Function[component, (#["Features"] -> #["Values"][component]) & /@ samples],
      targetComponents
    ];
    componentPredictors = AssociationMap[
      Predict[
        examplesByComponent[#],
        Method -> method,
        PerformanceGoal -> "TrainingSpeed",
        TrainingProgressReporting -> None
      ] &,
      targetComponents
    ];
    predictor = Function[
      featureVector,
      AssociationMap[
        Function[
          component,
          With[
            {value = Quiet@Check[N[componentPredictors[component][featureVector]], 0.0]},
            If[NumericQ[value], Max[0.0, value], 0.0]
          ]
        ],
        targetComponents
      ]
    ];
  ][[1]];
  <|
    "Predictor" -> predictor,
    "RegressionFunction" -> triPairShadowRegressionFunction[<|"Predictor" -> predictor|>],
    "ComponentPredictors" -> componentPredictors,
    "TargetComponents" -> targetComponents,
    "Pairs" -> pairs,
    "ExampleCount" -> Length[samples],
    "ElapsedSeconds" -> elapsed,
    "Options" -> <|
      "PairCount" -> pairCount,
      "OrientationSamples" -> sampleCount,
      "YawRange" -> yawRange,
      "PitchRange" -> pitchRange,
      "CriticalAngle" -> criticalAngle,
      "RandomSeed" -> seed,
      "Method" -> method,
      "TargetComponents" -> targetComponents
    |>
  |>
];

triPairShadowRegressionPrediction[triA_, triB_, center_, yaw_, pitch_, trained_] := Module[
  {predictor, features, prediction},
  predictor = If[AssociationQ[trained], trained["Predictor"], trained];
  features = triPairShadowRegressionFeatures[triA, triB, center, yaw, pitch];
  prediction = Quiet@Check[predictor[features], <|"v_ss" -> 0.0, "v_nv" -> 0.0|>];
  If[
    AssociationQ[prediction],
    Join[<|"v_ss" -> 0.0, "v_nv" -> 0.0|>, prediction],
    With[
      {value = Quiet@Check[N[prediction], 0.0]},
      <|"v_ss" -> If[NumericQ[value], Max[0.0, value], 0.0], "v_nv" -> 0.0|>
    ]
  ]
];

triPairShadowRegressionFunction[trained_] := Function[
  {localTriA, localTriB, center, yaw, pitch},
  triPairShadowRegressionPrediction[localTriA, localTriB, center, yaw, pitch, trained]
];

Options[regressionTriPairShadowGrid] = {"Component" -> "v_ss"};

regressionTriPairShadowGrid[triA_, triB_, center_, angleStep_, trained_, OptionsPattern[]] := Module[
  {component = OptionValue["Component"], yaws, pitches, grid},
  yaws = Range[0.0, 360.0, angleStep];
  pitches = Range[0.0, 360.0, angleStep];
  grid = Table[
    triPairShadowRegressionPrediction[triA, triB, center, yaw, pitch, trained][component],
    {pitch, pitches},
    {yaw, yaws}
  ];
  <|"YawValues" -> yaws, "PitchValues" -> pitches, "Grid" -> grid, "Component" -> component|>
];

Options[regressionTriPairShadowContour] = Join[
  Options[regressionTriPairShadowGrid],
  Options[ListContourPlot]
];

regressionTriPairShadowContour[triA_, triB_, center_, angleStep_, trained_, opts : OptionsPattern[]] := Module[
  {component = OptionValue["Component"], result, yaws, pitches, grid, plotOptions},
  result = regressionTriPairShadowGrid[triA, triB, center, angleStep, trained, "Component" -> component];
  yaws = result["YawValues"];
  pitches = result["PitchValues"];
  grid = result["Grid"];
  plotOptions = FilterRules[{opts}, Options[ListContourPlot]];
  ListContourPlot[
    grid,
    DataRange -> {{Min[yaws], Max[yaws]}, {Min[pitches], Max[pitches]}},
    FrameLabel -> Style[#, Black] & /@ {"Yaw angle (deg)", "Pitch angle (deg)"},
    PlotLabel -> Style["Regression-only " <> component <> " estimate", Black],
    ColorFunction -> "TemperatureMap",
    ColorFunctionScaling -> True,
    Contours -> 15,
    LabelStyle -> Black,
    PlotLegends -> Automatic,
    Sequence @@ plotOptions
  ]
];

triPairShadowRegressionDemo[] := Module[
  {trained, pair, vssPlot, vnvPlot},
  trained = trainTriPairShadowRegression[
    "PairCount" -> 100,
    "OrientationSamples" -> 5,
    "CriticalAngle" -> 60.0,
    "Method" -> "LinearRegression",
    "TargetComponents" -> {"v_ss", "v_nv"}
  ];
  pair = randomVisibleTrianglePair[];
  vssPlot = regressionTriPairShadowContour[
    pair["triA"], pair["triB"], pair["mcenter"], 5.0, trained,
    "Component" -> "v_ss",
    ImageSize -> 420
  ];
  vnvPlot = regressionTriPairShadowContour[
    pair["triA"], pair["triB"], pair["mcenter"], 5.0, trained,
    "Component" -> "v_nv",
    ImageSize -> 420
  ];
  <|"Training" -> trained, "TestPair" -> pair, "VssPlot" -> vssPlot, "VnvPlot" -> vnvPlot|>
];

showTriPairShadowRegressionDemo[] := Module[
  {demo, trained},
  demo = triPairShadowRegressionDemo[];
  trained = demo["Training"];
  Print[
    Row[{
      "trained regression: pairs=", Length[trained["Pairs"]],
      ", examples=", trained["ExampleCount"],
      ", targets=", StringRiffle[trained["TargetComponents"], ", "],
      ", elapsed=", NumberForm[trained["ElapsedSeconds"], {6, 3}], " s"
    }]
  ];
  GraphicsRow[{demo["VssPlot"], demo["VnvPlot"]}]
];
