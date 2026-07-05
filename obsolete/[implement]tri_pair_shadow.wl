ClearAll[
  loadTriPairShadowCore, projectRoot, defaultMeshPath, triangleFan,
  indexTriangleFan, trianglesFromMeshFile, meshRotationCenter, triangleAreaLocal,
  triangleNormalLocal, representativeVisiblePairs, contourAngleGrid,
  computeVisiblePairVssGrid, supportPrismPrimitive, renderShadowPreview,
  mergedVssContourPlot, runImplementTriPairShadow, showImplementTriPairShadowDemo
];

loadTriPairShadowCore[] := Module[
  {baseDir, path, text, prefixEnd},
  If[ValueQ[approximateSupportIntersectionVolume], Return[Null]];
  baseDir = If[StringQ[$InputFileName] && $InputFileName =!= "", DirectoryName[$InputFileName], Directory[]];
  path = FileNameJoin[{baseDir, "[function]tri_pair_shadow.wl"}];
  If[!FileExistsQ[path], path = FileNameJoin[{Directory[], "[function]tri_pair_shadow.wl"}]];
  If[!FileExistsQ[path], Print["Missing core file: ", path]; Return[$Failed]];
  text = Import[path, "Text"];
  prefixEnd = First@First@StringPosition[text, "\nblackNumber"];
  ToExpression[StringTake[text, prefixEnd - 1]];
];

projectRoot[] := If[
  StringQ[$InputFileName] && $InputFileName =!= "",
  DirectoryName[$InputFileName],
  Directory[]
];

defaultMeshPath[] := Module[
  {root = projectRoot[], candidates},
  candidates = {
    FileNameJoin[{root, "Experimental", "etc", "sphere5cm_f169.obj"}],
    FileNameJoin[{root, "Experimental", "etc", "(7)Bunny_1k.obj"}],
    FileNameJoin[{root, "Experimental", "etc", "box5cm_f16.obj"}]
  };
  SelectFirst[candidates, FileExistsQ, First[candidates]]
];

triangleFan[pts_] := If[
  Length[pts] == 3,
  {N[pts]},
  Table[N[{pts[[1]], pts[[i]], pts[[i + 1]]}], {i, 2, Length[pts] - 1}]
];

indexTriangleFan[ids_] := If[
  Length[ids] == 3,
  {ids},
  Table[{ids[[1]], ids[[i]], ids[[i + 1]]}, {i, 2, Length[ids] - 1}]
];

trianglesFromMeshFile[path_] := Module[
  {vertices, polygonData, mesh, normal, polygons, triangles},
  vertices = Quiet@Check[Import[path, "VertexData"], {}];
  polygonData = Quiet@Check[Import[path, "PolygonData"], {}];
  If[ListQ[vertices] && Length[vertices] > 0 && ListQ[polygonData] && Length[polygonData] > 0,
    triangles = Join @@ (indexTriangleFan /@ polygonData);
    Return[N[vertices[[#]]] & /@ triangles];
  ];
  mesh = Quiet@Check[Import[path], $Failed];
  If[mesh === $Failed, Print["Could not import mesh: ", path]; Return[{}]];
  normal = Quiet@Check[Normal[mesh], mesh];
  normal = normal /. GraphicsComplex[pts_, prim_] :> (prim /. i_Integer :> pts[[i]]);
  polygons = Cases[normal, Polygon[p_, ___] :> p, Infinity];
  triangles = Join @@ (triangleFan /@ polygons);
  DeleteCases[triangles, t_ /; Length[t] != 3]
];

meshRotationCenter[tris_] := Mean[Flatten[tris, 1]];

triangleAreaLocal[tri_] := Norm[Cross[tri[[2]] - tri[[1]], tri[[3]] - tri[[1]]]]/2.0;

triangleNormalLocal[tri_] := Module[
  {n = Cross[tri[[2]] - tri[[1]], tri[[3]] - tri[[1]]]},
  If[Norm[n] <= 10^-12, {0.0, 0.0, 1.0}, Normalize[n]]
];

representativeVisiblePairs[tris_, OptionsPattern[{
  "NormalLineDot" -> 0.15,
  "MaxPairs" -> 300
}]] := Module[
  {centers, normals, dotThreshold, maxPairs, candidates, dir, dist, score},
  centers = Mean /@ tris;
  normals = triangleNormalLocal /@ tris;
  dotThreshold = OptionValue["NormalLineDot"];
  maxPairs = OptionValue["MaxPairs"];
  candidates = Reap[
    Do[
      dir = centers[[j]] - centers[[i]];
      dist = Norm[dir];
      If[dist > 10^-12,
        dir = dir/dist;
        score = Max[
          normals[[i]].dir - normals[[j]].dir,
          -normals[[i]].dir + normals[[j]].dir
        ];
        If[score >= 2.0 dotThreshold, Sow[{score, i, j, dist}]];
      ],
      {i, 1, Length[tris] - 1},
      {j, i + 1, Length[tris]}
    ]
  ][[2]];
  If[candidates === {}, Return[{}]];
  candidates = First[candidates];
  candidates = Reverse@SortBy[candidates, First];
  DeleteDuplicatesBy[candidates[[All, {2, 3}]], Sort][[;; Min[maxPairs, Length[candidates]]]]
];

contourAngleGrid[angleStep_] := Range[0.0, 360.0, angleStep];

Options[computeVisiblePairVssGrid] = {
  "CriticalAngle" -> 60.0,
  "ApproximationOrder" -> 0,
  "ProgressPrint" -> True
};

computeVisiblePairVssGrid[
  tris_, pairFaces_, center_, yaws_, pitches_, OptionsPattern[]
] := Module[
  {criticalAngle = OptionValue["CriticalAngle"], order = OptionValue["ApproximationOrder"],
   progressQ = TrueQ[OptionValue["ProgressPrint"]], grid, pairMax, pairSum, pairStats,
   count = 0, total},
  loadTriPairShadowCore[];
  grid = ConstantArray[0.0, {Length[pitches], Length[yaws]}];
  pairMax = ConstantArray[0.0, Length[pairFaces]];
  pairSum = ConstantArray[0.0, Length[pairFaces]];
  total = Length[pitches] Length[yaws];
  Do[
    Module[{sum = 0.0, volume, faceI, faceJ},
      Do[
        {faceI, faceJ} = pairFaces[[pairId]];
        volume = N@approximateSupportIntersectionVolume[
          yaw, pitch, tris[[faceI]], tris[[faceJ]], center,
          "CriticalAngle" -> criticalAngle,
          "ApproximationOrder" -> order
        ];
        sum += volume;
        pairMax[[pairId]] = Max[pairMax[[pairId]], volume];
        pairSum[[pairId]] = pairSum[[pairId]] + volume;
        ,
        {pairId, Length[pairFaces]}
      ];
      grid[[pitchId, yawId]] = sum;
    ];
    count++;
    If[progressQ && (Mod[count, 25] == 0 || count == total),
      Print["merged v_ss orientations: ", count, "/", total]
    ];
    ,
    {pitchId, Length[pitches]}, {yawId, Length[yaws]},
    {pitch, {pitches[[pitchId]]}}, {yaw, {yaws[[yawId]]}}
  ];
  pairStats = Association@Table[
    k -> <|"MaxVolume" -> pairMax[[k]], "SumVolume" -> pairSum[[k]]|>,
    {k, Length[pairFaces]}
  ];
  <|
    "Grid" -> grid,
    "PairStats" -> pairStats
  |>
];

supportPrismPrimitive[sourceTri_, targetTri_, center_, yawDeg_, pitchDeg_] := Module[
  {rotatedSource, rotatedTarget, verticalAxis = {0.0, 0.0, 1.0}, pairVector, deltaZ, top},
  loadTriPairShadowCore[];
  rotatedSource = rotateTriangle[sourceTri, center, yawDeg, pitchDeg];
  rotatedTarget = rotateTriangle[targetTri, center, yawDeg, pitchDeg];
  pairVector = Mean[rotatedTarget] - Mean[rotatedSource];
  deltaZ = verticalAxis.pairVector;
  top = (# + deltaZ verticalAxis) & /@ rotatedSource;
  Prism[Join[rotatedSource, top]]
];

renderShadowPreview[result_, OptionsPattern[{
  "Yaw" -> 0.0,
  "Pitch" -> 0.0,
  "MaxRenderedPairs" -> 80,
  "ImageSize" -> 760
}]] := Module[
  {tris = result["Triangles"], center = result["Center"], pairFaces = result["PairFaces"],
   pairStats = result["PairStats"], yaw = OptionValue["Yaw"], pitch = OptionValue["Pitch"],
   maxPairs = OptionValue["MaxRenderedPairs"], ranked, selected},
  ranked = Reverse@SortBy[Keys[pairStats], pairStats[#]["MaxVolume"] &];
  selected = Take[Select[ranked, pairStats[#]["MaxVolume"] > 0.0 &], UpTo[maxPairs]];
  Graphics3D[
    {
      Opacity[0.28], LightGray, Polygon /@ tris,
      Opacity[0.30], Darker[Green],
      Table[
        supportPrismPrimitive[
          tris[[pairFaces[[pairId, 1]]]],
          tris[[pairFaces[[pairId, 2]]]],
          center, yaw, pitch
        ],
        {pairId, selected}
      ]
    },
    Boxed -> True,
    Axes -> True,
    ImageSize -> OptionValue["ImageSize"]
  ]
];

mergedVssContourPlot[result_, OptionsPattern[{
  "Contours" -> 15,
  "ImageSize" -> 900
}]] := Module[
  {yaws = result["YawValues"], pitches = result["PitchValues"], grid = result["MergedVss"]},
  ListContourPlot[
    grid,
    DataRange -> {{Min[yaws], Max[yaws]}, {Min[pitches], Max[pitches]}},
    FrameLabel -> Style[#, Black] & /@ {"Yaw angle (deg)", "Pitch angle (deg)"},
    PlotLabel -> Style[
      Row[{result["Label"], " merged visible-face pair v_ss"}],
      Black
    ],
    ColorFunction -> "TemperatureMap",
    ColorFunctionScaling -> True,
    Contours -> OptionValue["Contours"],
    LabelStyle -> Black,
    PlotLegends -> Automatic,
    ImageSize -> OptionValue["ImageSize"]
  ]
];

Options[runImplementTriPairShadow] = {
  "MeshPath" :> defaultMeshPath[],
  "CriticalAngle" -> 60.0,
  "AngleStep" -> 45.0,
  "ApproximationOrder" -> 0,
  "NormalLineDot" -> 0.15,
  "MaxPairs" -> 300,
  "OutputDirectory" -> FileNameJoin[{projectRoot[], "comparison_outputs", "tri_pair_shadow_regression"}],
  "ExportContour" -> True,
  "ProgressPrint" -> True
};

runImplementTriPairShadow[OptionsPattern[]] := Module[
  {meshPath = OptionValue["MeshPath"], criticalAngle = OptionValue["CriticalAngle"],
   angleStep = OptionValue["AngleStep"], order = OptionValue["ApproximationOrder"],
   outputDir = OptionValue["OutputDirectory"], label, tris, center, pairFaces,
   yaws, pitches, gridResult, result, outPath},
  loadTriPairShadowCore[];
  label = FileBaseName[meshPath];
  Print["=== tri-pair shadow implement ==="];
  Print["mesh=", meshPath];
  tris = trianglesFromMeshFile[meshPath];
  If[Length[tris] == 0, Print["No triangles loaded."]; Return[$Failed]];
  center = meshRotationCenter[tris];
  pairFaces = representativeVisiblePairs[
    tris,
    "NormalLineDot" -> OptionValue["NormalLineDot"],
    "MaxPairs" -> OptionValue["MaxPairs"]
  ];
  Print["visible pair proxy count: ", Length[pairFaces]];
  yaws = contourAngleGrid[angleStep];
  pitches = contourAngleGrid[angleStep];
  gridResult = computeVisiblePairVssGrid[
    tris, pairFaces, center, yaws, pitches,
    "CriticalAngle" -> criticalAngle,
    "ApproximationOrder" -> order,
    "ProgressPrint" -> OptionValue["ProgressPrint"]
  ];
  result = <|
    "MeshPath" -> meshPath,
    "Label" -> label,
    "Triangles" -> tris,
    "Center" -> center,
    "PairFaces" -> pairFaces,
    "YawValues" -> yaws,
    "PitchValues" -> pitches,
    "MergedVss" -> gridResult["Grid"],
    "PairStats" -> gridResult["PairStats"],
    "CriticalAngle" -> criticalAngle,
    "AngleStep" -> angleStep,
    "ApproximationOrder" -> order
  |>;
  Print[
    "merged contour grid: shape={", Length[pitches], ", ", Length[yaws], "}, min=",
    Min[Flatten[result["MergedVss"]]], ", max=", Max[Flatten[result["MergedVss"]]],
    ", sum=", Total[Flatten[result["MergedVss"]]]
  ];
  If[TrueQ[OptionValue["ExportContour"]],
    If[!DirectoryQ[outputDir], CreateDirectory[outputDir, CreateIntermediateDirectories -> True]];
    outPath = FileNameJoin[{outputDir, "tri_pair_shadow_merged_v_ss_contour_wl.html"}];
    Export[outPath, mergedVssContourPlot[result]];
    Print["wrote ", outPath];
  ];
  result
];

showImplementTriPairShadowDemo[opts : OptionsPattern[runImplementTriPairShadow]] := Module[
  {result},
  result = runImplementTriPairShadow[opts];
  If[result === $Failed, Return[$Failed]];
  Column[
    {
      mergedVssContourPlot[result],
      renderShadowPreview[result]
    }
  ]
];
