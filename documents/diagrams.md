
# Kabaddi Ghost Trainer - Block Diagrams

## Module 1: Pose Extraction & Cleaning (YOLO Player Identification)

```mermaid
flowchart LR
    %% Nodes
    A[/Raw Kabaddi Video/]
    B(YOLOv8 Person Detection)
    C(ByteTrack Multi-Object Tracking)
    D(Motion-Based Raider Selection)
    E[/Raider Bounding Box Sequence/]

    %% Edges
    A -- "RGB Frames" --> B
    B -- "Detections (BBoxes)" --> C
    C -- "Track IDs + BBoxes" --> D
    D -- "Raider ID" --> E

    %% Styling
    classDef blueInput fill:#dae8fc,stroke:#6c8ebf,color:black,shape:parallelogram;
    classDef purpleProcess fill:#e1d5e7,stroke:#9673a6,color:black,rx:10,ry:10;
    classDef darkBlueOutput fill:#bac8d3,stroke:#23445d,color:black,shape:parallelogram;

    class A blueInput;
    class B,C,D purpleProcess;
    class E darkBlueOutput;
```

## Module 1: Pose Extraction (Pose Estimation)

```mermaid
flowchart LR
    %% Nodes
    A[/Raider Bounding Box Sequence/]
    B(Frame-wise Raider Cropping)
    C(MediaPipe Pose Estimation MP33)
    D[/Raw Pose Keypoints 33 joints normalized/]

    %% Edges
    A -- "BBox Coordinates" --> B
    B -- "Cropped Raider Frame" --> C
    C -- "33 Keypoints (x,y) normalized" --> D


    %% Styling
    classDef input fill:#dae8fc,stroke:#6c8ebf,color:black,shape:parallelogram;
    classDef aiModel fill:#d5e8d4,stroke:#82b366,color:black,rx:10,ry:10;
    classDef output fill:#bac8d3,stroke:#23445d,color:black,shape:parallelogram;

    class A input;
    class B,C aiModel;
    class D output;
```

## Module 1: Pose Extraction (Format Conversion)

```mermaid
flowchart LR
    %% Nodes
    A[/Raw MP33 Pose Data Normalized/]
    B(Joint Index Mapping)
    C(Coordinate Transformation)
    D[/COCO-17 Pose Data Pixel Space/]

    %% Edges
    A -- "Normalized Keypoints" --> B
    B -- "Mapped Joints" --> C
    C -- "Pixel Coordinates" --> D

    %% Styling
    classDef input fill:#dae8fc,stroke:#6c8ebf,color:black,shape:parallelogram;
    classDef process fill:#e1d5e7,stroke:#9673a6,color:black,rx:10,ry:10;
    classDef output fill:#bac8d3,stroke:#23445d,color:black,shape:parallelogram;

    class A input;
    class B,C process;
    class D output;
```

## Module 1: Data Canonicalization & Cleaning (Part 1)

```mermaid
flowchart LR
    %% Nodes
    A[/Raw COCO-17 Pose Sequence/]
    B(Temporal Interpolation)
    C(Pelvis Centering)
    D[/Centered Pose Sequence/]

    %% Edges
    A -- "Raw Sequence" --> B
    B -- "Gap-Filled Pose" --> C
    C -- "Centered Pose" --> D

    %% Styling
    classDef input fill:#dae8fc,stroke:#6c8ebf,color:black,shape:parallelogram;
    classDef process fill:#e1d5e7,stroke:#9673a6,color:black,rx:10,ry:10;
    classDef output fill:#bac8d3,stroke:#23445d,color:black,shape:parallelogram;

    class A input;
    class B,C process;
    class D output;
```

## Module 1: Data Canonicalization & Cleaning (Part 2)

```mermaid
flowchart LR
    %% Nodes
    A[/Centered Pose Sequence/]
    D(Scale Normalization)
    E(Outlier Suppression)
    F(EMA Smoothing)
    G[(Cleaned & Normalized Pose)]

    %% Edges
    A --> D
    D -- "Normalized Pose" --> E
    E -- "Outlier-Free Pose" --> F
    F -- "Smoothed Pose" --> G

    %% Styling
    classDef input fill:#bac8d3,stroke:#23445d,color:black,shape:parallelogram;
    classDef process fill:#e1d5e7,stroke:#9673a6,color:black,rx:10,ry:10;
    classDef storage fill:#fff2cc,stroke:#d6b656,color:black,shape:cylinder;

    class A input;
    class D,E,F process;
    class G storage;
```

## Module 2: Temporal Alignment (Pelvis Trajectory Extraction)

```mermaid
flowchart LR
    %% Nodes
    A[/Cleaned COCO-17 Pose Sequence/]
    B(Left Hip + Right Hip Selection)
    C(Pelvis Midpoint Computation)
    D[/Pelvis Trajectory T x 2/]

    %% Edges
    A -- "Full Pose Sequence" --> B
    B -- "Hip Coordinates" --> C
    C -- "Midpoint (x,y)" --> D

    %% Styling
    classDef input fill:#dae8fc,stroke:#6c8ebf,color:black,shape:parallelogram;
    classDef process fill:#e1d5e7,stroke:#9673a6,color:black,rx:10,ry:10;
    classDef output fill:#bac8d3,stroke:#23445d,color:black,shape:parallelogram;

    class A input;
    class B,C process;
    class D output;
```

## Module 2: Dynamic Time Warping (DTW)

```mermaid
flowchart LR
    %% Nodes
    A[/Expert Pelvis Trajectory/]
    C[/User Pelvis Trajectory/]
    B(DTW Cost Matrix Computation)
    D[/Optimal Alignment Path/]
    E[/Aligned Frame Index Pairs/]

    %% Edges
    A --> B
    C --> B
    B -- "Cost Matrix" --> D
    D -- "Traceback" --> E

    %% Styling
    classDef input fill:#dae8fc,stroke:#6c8ebf,color:black,shape:parallelogram;
    classDef process fill:#e1d5e7,stroke:#9673a6,color:black,rx:10,ry:10;
    classDef output fill:#bac8d3,stroke:#23445d,color:black,shape:parallelogram;

    class A,C input;
    class B process;
    class D,E output;
```

## Module 2: Aligned Pose Generation

```mermaid
 flowchart LR
     %% Nodes
     A[/Expert Pose Sequence/]
     C[/User Pose Sequence/]
     B(DTW Alignment Indices)
     D(Index-Based Pose Extraction)
     E[/Aligned Expert & User Poses/]

     %% Edges
     A --> D
     C --> D
     B --> D
     D -- "Synchronized" --> E

     %% Styling
     classDef input fill:#dae8fc,stroke:#6c8ebf,color:black,shape:parallelogram;
     classDef process fill:#e1d5e7,stroke:#9673a6,color:black,rx:10,ry:10;
     classDef output fill:#bac8d3,stroke:#23445d,color:black,shape:parallelogram;

     class A,C input;
     class B,D process;
     class E output;
```

## Module 3: Error Computation Engine

```mermaid
flowchart LR
    %% Nodes
    A[/Aligned Expert Pose/]
    C[/Aligned User Pose/]
    B(Euclidean Distance Computation)
    D[(Error Matrix T x 17)]

    %% Edges
    A --> B
    C --> B
    B -- "Vector Distances" --> D

    %% Styling
    classDef input fill:#dae8fc,stroke:#6c8ebf,color:black,shape:parallelogram;
    classDef process fill:#e1d5e7,stroke:#9673a6,color:black,rx:10,ry:10;
    classDef storage fill:#fff2cc,stroke:#d6b656,color:black,shape:cylinder;

    class A,C input;
    class B process;
    class D storage;
```

## Module 3: Error Aggregation & Statistics

```mermaid
flowchart LR
    %% Nodes
    A[(Joint Error Matrix)]
    B(Statistical Aggregation)
    Out(( ))
    classDef invisible fill:none,stroke:none;
    class Out invisible;
    C[(Joint Stats)]
    D[(Frame Stats)]
    E[(Phase Stats)]

    %% Edges
    A --> B
    B --> Out
    Out --> C
    Out --> D
    Out --> E

    %% Styling
    classDef input fill:#fff2cc,stroke:#d6b656,color:black,shape:cylinder;
    classDef process fill:#e1d5e7,stroke:#9673a6,color:black,rx:10,ry:10;
    classDef output fill:#fff2cc,stroke:#d6b656,color:black,shape:cylinder;
    classDef invisible fill:none,stroke:none;

    class A input;
    class B process;
    class Out invisible;
    class C,D,E output;
```

## Module 3: Data Serialization

```mermaid
flowchart LR
    %% Nodes
    A[(Joint Error Matrix)]
    B[(Joint Stats)]
    C[(Frame Stats)]
    D[(Phase Stats)]
    E(Structured Data Packaging)
    F[(joint_errors.json)]

    %% Edges
    A --> E
    B --> E
    C --> E
    D --> E
    E -- "JSON Object" --> F

    %% Styling
    classDef input fill:#fff2cc,stroke:#d6b656,color:black,shape:cylinder;
    classDef process fill:#e1d5e7,stroke:#9673a6,color:black,rx:10,ry:10;
    classDef output fill:#fff2cc,stroke:#d6b656,color:black,shape:cylinder;

    class A,B,C,D input;
    class E process;
    class F output;
```

## Module 4: Similarity Scoring Engine

```mermaid
flowchart LR
    %% Nodes
    A[(joint_errors.json)]
    B(Structural Similarity)
    C(Temporal Similarity)
    D(Weighted Score Aggregation)
    E[/Similarity Scores/]

    %% Edges
    A --> B
    A --> C
    B --> D
    C --> D
    D -- "Final Score" --> E

    %% Styling
    classDef input fill:#fff2cc,stroke:#d6b656,color:black,shape:cylinder;
    classDef process fill:#e1d5e7,stroke:#9673a6,color:black,rx:10,ry:10;
    classDef output fill:#bac8d3,stroke:#23445d,color:black,shape:parallelogram;

    class A input;
    class B,C,D process;
    class E output;
```
