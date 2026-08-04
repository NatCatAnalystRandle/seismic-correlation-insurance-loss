import gov.usgs.earthquake.nshmp.fault.surface.RuptureSurface;
import gov.usgs.earthquake.nshmp.geo.Location;
import gov.usgs.earthquake.nshmp.model.Distance;
import gov.usgs.earthquake.nshmp.model.HazardModel;
import gov.usgs.earthquake.nshmp.model.Rupture;
import gov.usgs.earthquake.nshmp.model.RuptureSet;
import gov.usgs.earthquake.nshmp.model.Source;
import gov.usgs.earthquake.nshmp.model.SourceTree;
import gov.usgs.earthquake.nshmp.tree.Branch;

import java.io.BufferedReader;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;

public final class ControlledRuptureRetrieval {

  private ControlledRuptureRetrieval() {}

  public static void main(String[] args) throws Exception {

    if (args.length != 3) {
      throw new IllegalArgumentException(
          "Expected model root, input TSV, and output CSV.");
    }

    Path modelRoot = Path.of(args[0])
        .toAbsolutePath()
        .normalize();

    Path inputPath = Path.of(args[1])
        .toAbsolutePath()
        .normalize();

    Path outputPath = Path.of(args[2])
        .toAbsolutePath()
        .normalize();

    Files.createDirectories(
        outputPath.getParent());

    HazardModel model =
        HazardModel.load(modelRoot);

    int rowCount = 0;

    try (
        BufferedReader reader =
            Files.newBufferedReader(
                inputPath,
                StandardCharsets.UTF_8);

        PrintWriter writer =
            new PrintWriter(
                Files.newBufferedWriter(
                    outputPath,
                    StandardCharsets.UTF_8))
    ) {

      String headerLine = reader.readLine();

      if (headerLine == null) {
        throw new IllegalArgumentException(
            "Input TSV is empty.");
      }

      String[] header =
          headerLine.split("\t", -1);

      Map<String, Integer> columnMap =
          new HashMap<>();

      for (int i = 0; i < header.length; i++) {
        columnMap.put(header[i], i);
      }

      writer.println(String.join(",",
          "case_id",
          "event_id",
          "rupture_id",
          "expected_tree_id",
          "retrieved_tree_id",
          "expected_branch_index",
          "retrieved_branch_id",
          "retrieved_branch_weight",
          "expected_rupture_set_id",
          "retrieved_rupture_set_id",
          "retrieved_rupture_set_name",
          "expected_source_index",
          "expected_source_id",
          "retrieved_source_id",
          "expected_source_name",
          "retrieved_source_name",
          "expected_source_type",
          "retrieved_source_type",
          "expected_rupture_index",
          "expected_magnitude",
          "retrieved_magnitude",
          "expected_raw_rate",
          "retrieved_raw_rate",
          "retrieved_rake_deg",
          "surface_class",
          "expected_top_depth_km",
          "surface_depth_km",
          "expected_width_km",
          "surface_width_km",
          "surface_dip_deg",
          "surface_strike_deg",
          "expected_centroid_longitude",
          "surface_centroid_longitude",
          "expected_centroid_latitude",
          "surface_centroid_latitude",
          "expected_centroid_depth_km",
          "surface_centroid_depth_km",
          "test_site_id",
          "test_site_longitude",
          "test_site_latitude",
          "r_jb_km",
          "r_rup_km",
          "r_x_km",
          "retrieval_error"
      ));

      String line;

      while ((line = reader.readLine()) != null) {

        if (line.isBlank()) {
          continue;
        }

        String[] values =
            line.split("\t", -1);

        String caseId =
            get(values, columnMap, "case_id");

        String eventId =
            get(values, columnMap, "event_id");

        String ruptureId =
            get(values, columnMap, "rupture_id");

        int treeId =
            parseInt(
                get(values, columnMap, "tree_id"));

        int branchIndex =
            parseInt(
                get(values, columnMap, "branch_index"));

        int expectedRuptureSetId =
            parseInt(
                get(values, columnMap, "rupture_set_id"));

        int sourceIndex =
            parseInt(
                get(values, columnMap, "source_index"));

        int expectedSourceId =
            parseInt(
                get(values, columnMap, "source_id"));

        int ruptureIndex =
            parseInt(
                get(values, columnMap, "rupture_index"));

        String expectedSourceName =
            get(values, columnMap, "source_name");

        String expectedSourceType =
            get(values, columnMap, "source_type");

        double expectedMagnitude =
            parseDouble(
                get(values, columnMap, "magnitude"));

        double expectedRawRate =
            parseDouble(
                get(values, columnMap, "raw_annual_rate"));

        double expectedTopDepth =
            parseDouble(
                get(values, columnMap, "top_depth_km"));

        double expectedWidth =
            parseDouble(
                get(values, columnMap, "width_km"));

        double expectedCentroidLongitude =
            parseDoubleOrNaN(
                get(values, columnMap, "centroid_longitude"));

        double expectedCentroidLatitude =
            parseDoubleOrNaN(
                get(values, columnMap, "centroid_latitude"));

        double expectedCentroidDepth =
            parseDoubleOrNaN(
                get(values, columnMap, "centroid_depth_km"));

        String testSiteId =
            get(values, columnMap, "test_site_id");

        double testSiteLongitude =
            parseDouble(
                get(values, columnMap, "test_site_longitude"));

        double testSiteLatitude =
            parseDouble(
                get(values, columnMap, "test_site_latitude"));

        int retrievedTreeId = -1;
        String branchId = "";
        double branchWeight = Double.NaN;
        int retrievedRuptureSetId = -1;
        String retrievedRuptureSetName = "";
        int retrievedSourceId = -1;
        String retrievedSourceName = "";
        String retrievedSourceType = "";
        double retrievedMagnitude = Double.NaN;
        double retrievedRate = Double.NaN;
        double retrievedRake = Double.NaN;
        String surfaceClass = "";
        double surfaceDepth = Double.NaN;
        double surfaceWidth = Double.NaN;
        double surfaceDip = Double.NaN;
        double surfaceStrike = Double.NaN;
        double surfaceCentroidLongitude = Double.NaN;
        double surfaceCentroidLatitude = Double.NaN;
        double surfaceCentroidDepth = Double.NaN;
        double rJB = Double.NaN;
        double rRup = Double.NaN;
        double rX = Double.NaN;
        String retrievalError = "";

try {

  Optional<SourceTree> treeOptional =
      model.tree(treeId);

  if (treeOptional.isEmpty()) {
    throw new IllegalArgumentException(
        "Tree not found: " + treeId);
  }

  SourceTree tree =
      treeOptional.get();

  retrievedTreeId =
      tree.id();

  Branch<RuptureSet<? extends Source>> branch =
      null;

  int ruptureSetIdMatchCount = 0;
  int compatibleBranchCount = 0;

  for (int index = 0; index < tree.size(); index++) {

    Branch<RuptureSet<? extends Source>> candidate =
        tree.get(index);

    RuptureSet<? extends Source> candidateRuptureSet =
        candidate.value();

    if (
        candidateRuptureSet.id()
        != expectedRuptureSetId
    ) {
      continue;
    }

    ruptureSetIdMatchCount++;

    if (
        sourceIndex < 0
        || sourceIndex >= candidateRuptureSet.size()
    ) {
      continue;
    }

    Source candidateSource =
        candidateRuptureSet.get(sourceIndex);

    if (
        candidateSource.id()
        != expectedSourceId
    ) {
      continue;
    }

    if (
        !candidateSource.name().equals(
            expectedSourceName)
    ) {
      continue;
    }

    if (
        ruptureIndex < 0
        || ruptureIndex >= candidateSource.size()
    ) {
      continue;
    }

    Rupture candidateRupture =
        candidateSource.get(ruptureIndex);

    boolean magnitudeMatches =
        Math.abs(
            candidateRupture.mag()
            - expectedMagnitude
        ) <= 1.0e-10;

    double rateScale =
        Math.max(
            Math.abs(candidateRupture.rate()),
            Math.abs(expectedRawRate)
        );

    double rateTolerance =
        Math.max(
            1.0e-18,
            1.0e-12 * rateScale
        );

    boolean rateMatches =
        Math.abs(
            candidateRupture.rate()
            - expectedRawRate
        ) <= rateTolerance;

    if (
        !magnitudeMatches
        || !rateMatches
    ) {
      continue;
    }

    if (branch == null) {
      branch =
          candidate;
    }

    compatibleBranchCount++;
  }

  if (branch == null) {

    throw new IllegalArgumentException(
        "No compatible branch was found for "
        + "rupture-set ID "
        + expectedRuptureSetId
        + " in tree "
        + treeId
        + ". Rupture-set ID matches: "
        + ruptureSetIdMatchCount
        + ", compatible matches: "
        + compatibleBranchCount);
  }

  branchId =
      branch.id();

  branchWeight =
      branch.weight();

  RuptureSet<? extends Source> ruptureSet =
      branch.value();

  retrievedRuptureSetId =
      ruptureSet.id();

  retrievedRuptureSetName =
      ruptureSet.name();

  Source source =
      ruptureSet.get(sourceIndex);

  retrievedSourceId =
      source.id();

  retrievedSourceName =
      source.name();

  retrievedSourceType =
      source.type().name();

  Rupture rupture =
      source.get(ruptureIndex);

  retrievedMagnitude =
      rupture.mag();

  retrievedRate =
      rupture.rate();

  retrievedRake =
      rupture.rake();

  RuptureSurface surface =
      rupture.surface();

  Location site =
      Location.create(
          testSiteLongitude,
          testSiteLatitude);

  Distance distance =
      surface.distanceTo(site);

  rJB =
      distance.rJB;

  rRup =
      distance.rRup;

  rX =
      distance.rX;

  surfaceClass =
      surface.getClass().getName();

  surfaceDepth =
      safeSurfaceValue(
          () -> surface.depth());

  surfaceWidth =
      safeSurfaceValue(
          () -> surface.width());

  surfaceDip =
      safeSurfaceValue(
          () -> surface.dip());

  surfaceStrike =
      safeSurfaceValue(
          () -> surface.strike());

  try {

    Location centroid =
        surface.centroid();

    if (centroid != null) {

      surfaceCentroidLongitude =
          centroid.longitude;

      surfaceCentroidLatitude =
          centroid.latitude;

      surfaceCentroidDepth =
          centroid.depth;
    }

  } catch (RuntimeException exception) {

    surfaceCentroidLongitude =
        Double.NaN;

    surfaceCentroidLatitude =
        Double.NaN;

    surfaceCentroidDepth =
        Double.NaN;
  }

} catch (Exception exception) {

  retrievalError =
      exception.getClass().getName()
      + ": "
      + String.valueOf(
          exception.getMessage());
}

        writer.println(String.join(",",
            csv(caseId),
            csv(eventId),
            csv(ruptureId),
            integer(treeId),
            integer(retrievedTreeId),
            integer(branchIndex),
            csv(branchId),
            number(branchWeight),
            integer(expectedRuptureSetId),
            integer(retrievedRuptureSetId),
            csv(retrievedRuptureSetName),
            integer(sourceIndex),
            integer(expectedSourceId),
            integer(retrievedSourceId),
            csv(expectedSourceName),
            csv(retrievedSourceName),
            csv(expectedSourceType),
            csv(retrievedSourceType),
            integer(ruptureIndex),
            number(expectedMagnitude),
            number(retrievedMagnitude),
            number(expectedRawRate),
            number(retrievedRate),
            number(retrievedRake),
            csv(surfaceClass),
            number(expectedTopDepth),
            number(surfaceDepth),
            number(expectedWidth),
            number(surfaceWidth),
            number(surfaceDip),
            number(surfaceStrike),
            number(expectedCentroidLongitude),
            number(surfaceCentroidLongitude),
            number(expectedCentroidLatitude),
            number(surfaceCentroidLatitude),
            number(expectedCentroidDepth),
            number(surfaceCentroidDepth),
            csv(testSiteId),
            number(testSiteLongitude),
            number(testSiteLatitude),
            number(rJB),
            number(rRup),
            number(rX),
            csv(retrievalError)
        ));

        rowCount++;
      }
    }

    System.out.println(
        "CONTROLLED_RUPTURE_RETRIEVAL_COMPLETE");

    System.out.println(
        "rows=" + rowCount);

    System.out.println(
        "model_root=" + modelRoot);

    System.out.println(
        "output=" + outputPath);
  }

  private static double safeSurfaceValue(
    java.util.function.DoubleSupplier supplier
) {

  try {

    return supplier.getAsDouble();

  } catch (RuntimeException exception) {

    return Double.NaN;
  }
}

private static String get(
    String[] values,
    Map<String, Integer> columnMap,
    String name
) {

    Integer index =
        columnMap.get(name);

    if (index == null) {
      throw new IllegalArgumentException(
          "Missing input column: " + name);
    }

    return values[index];
  }

  private static int parseInt(
      String value
  ) {
    return (int) Math.round(
        Double.parseDouble(value));
  }

  private static double parseDouble(
      String value
  ) {
    return Double.parseDouble(value);
  }

  private static double parseDoubleOrNaN(
      String value
  ) {

    if (value == null || value.isBlank()) {
      return Double.NaN;
    }

    return Double.parseDouble(value);
  }

  private static String integer(
      int value
  ) {
    return Integer.toString(value);
  }

  private static String number(
      double value
  ) {
    return String.format(
        Locale.US,
        "%.17g",
        value);
  }

  private static String csv(
      String value
  ) {

    if (value == null) {
      return "";
    }

    boolean quote =
        value.contains(",")
        || value.contains("\"")
        || value.contains("\n")
        || value.contains("\r");

    if (!quote) {
      return value;
    }

    return "\""
        + value.replace("\"", "\"\"")
        + "\"";
  }
}
