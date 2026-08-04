import gov.usgs.earthquake.nshmp.fault.surface.RuptureSurface;
import gov.usgs.earthquake.nshmp.geo.Location;
import gov.usgs.earthquake.nshmp.model.HazardModel;
import gov.usgs.earthquake.nshmp.model.Rupture;
import gov.usgs.earthquake.nshmp.model.RuptureSet;
import gov.usgs.earthquake.nshmp.model.Source;
import gov.usgs.earthquake.nshmp.model.SourceTree;
import gov.usgs.earthquake.nshmp.tree.Branch;

import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.Locale;

public final class RuptureRateExporter {

  private static final String HEADER = String.join(",",
      "rupture_id",
      "target_group",
      "model_name",
      "tree_id",
      "tree_name",
      "tree_path",
      "tree_type",
      "tectonic_setting",
      "branch_index",
      "branch_weight",
      "rupture_set_id",
      "rupture_set_name",
      "rupture_set_type",
      "rupture_set_weight",
      "source_index",
      "source_id",
      "source_name",
      "source_type",
      "rupture_index",
      "magnitude",
      "rake_deg",
      "raw_annual_rate",
      "weighted_annual_rate",
      "centroid_longitude",
      "centroid_latitude",
      "centroid_depth_km",
      "top_depth_km",
      "strike_deg",
      "dip_deg",
      "dip_direction_deg",
      "length_km",
      "width_km",
      "area_km2"
  );

  private RuptureRateExporter() {}

  public static void main(String[] args) throws Exception {

    if (args.length != 2) {
      System.err.println(
          "Usage: RuptureRateExporter <model-directory> <output-csv>");
      System.exit(2);
    }

    Path modelPath = Path.of(args[0]).toAbsolutePath().normalize();
    Path outputPath = Path.of(args[1]).toAbsolutePath().normalize();

    if (!Files.isDirectory(modelPath)) {
      throw new IllegalArgumentException(
          "Model directory does not exist: " + modelPath);
    }

    if (outputPath.getParent() != null) {
      Files.createDirectories(outputPath.getParent());
    }

    System.out.println("Loading model: " + modelPath);
    System.out.println("Started: " + Instant.now());

    HazardModel model = HazardModel.load(modelPath);

    long selectedTreeCount = 0;
    long ruptureSetCount = 0;
    long sourceCount = 0;
    long ruptureCount = 0;
    long interfaceCount = 0;
    long slabCount = 0;

    double rawRateSum = 0.0;
    double weightedRateSum = 0.0;

    try (
        PrintWriter writer = new PrintWriter(
            Files.newBufferedWriter(
                outputPath,
                StandardCharsets.UTF_8))
    ) {

      writer.println(HEADER);

      for (SourceTree tree : model) {

        String treePath = normalizePath(
            tree.path().toString());

        String treeType = tree.type().name();

        String targetGroup = targetGroup(
            treeType,
            treePath);

        if (targetGroup == null) {
          continue;
        }

        selectedTreeCount++;

        System.out.println(
            "Selected tree: "
            + treeType
            + " | "
            + treePath);

        for (
            int branchIndex = 0;
            branchIndex < tree.size();
            branchIndex++
        ) {

          Branch<RuptureSet<? extends Source>> branch =
              tree.get(branchIndex);

          RuptureSet<? extends Source> ruptureSet =
              branch.value();

          double branchWeight = branch.weight();
          double ruptureSetWeight = ruptureSet.weight();

          ruptureSetCount++;

          for (
              int sourceIndex = 0;
              sourceIndex < ruptureSet.size();
              sourceIndex++
          ) {

            Source source = ruptureSet.get(
                sourceIndex);

            sourceCount++;

            for (
                int ruptureIndex = 0;
                ruptureIndex < source.size();
                ruptureIndex++
            ) {

              Rupture rupture = source.get(
                  ruptureIndex);

              double rawRate = rupture.rate();

              // The rupture-set weight is applied once.
              double weightedRate =
                  rawRate * ruptureSetWeight;

              SurfaceValues geometry =
                  SurfaceValues.from(
                      rupture.surface());

              String stableKey = String.join("|",
                  model.name(),
                  Integer.toString(tree.id()),
                  treePath,
                  Integer.toString(branchIndex),
                  Integer.toString(ruptureSet.id()),
                  Integer.toString(sourceIndex),
                  Integer.toString(source.id()),
                  Integer.toString(ruptureIndex),
                  Double.toString(rupture.mag()),
                  Double.toString(rupture.rake()),
                  number(geometry.longitude),
                  number(geometry.latitude),
                  number(geometry.centroidDepth)
              );

              String ruptureId = sha256(
                  stableKey).substring(0, 24);

              writer.println(String.join(",",
                  csv(ruptureId),
                  csv(targetGroup),
                  csv(model.name()),
                  integer(tree.id()),
                  csv(tree.name()),
                  csv(treePath),
                  csv(treeType),
                  csv(tree.setting().name()),
                  integer(branchIndex),
                  number(branchWeight),
                  integer(ruptureSet.id()),
                  csv(ruptureSet.name()),
                  csv(ruptureSet.type().name()),
                  number(ruptureSetWeight),
                  integer(sourceIndex),
                  integer(source.id()),
                  csv(source.name()),
                  csv(source.type().name()),
                  integer(ruptureIndex),
                  number(rupture.mag()),
                  number(rupture.rake()),
                  number(rawRate),
                  number(weightedRate),
                  number(geometry.longitude),
                  number(geometry.latitude),
                  number(geometry.centroidDepth),
                  number(geometry.topDepth),
                  number(geometry.strike),
                  number(geometry.dip),
                  number(geometry.dipDirection),
                  number(geometry.length),
                  number(geometry.width),
                  number(geometry.area)
              ));

              ruptureCount++;
              rawRateSum += rawRate;
              weightedRateSum += weightedRate;

              if (
                  targetGroup.equals(
                      "cascadia_interface")
              ) {
                interfaceCount++;
              } else {
                slabCount++;
              }
            }
          }
        }
      }
    }

    if (selectedTreeCount == 0) {
      throw new IllegalStateException(
          "No Cascadia interface or Oregon slab trees were selected.");
    }

    if (ruptureCount == 0) {
      throw new IllegalStateException(
          "The selected source trees produced no ruptures.");
    }

    System.out.println();
    System.out.println("EXPORT_COMPLETE");
    System.out.println(
        "selected_trees=" + selectedTreeCount);
    System.out.println(
        "rupture_sets=" + ruptureSetCount);
    System.out.println(
        "sources=" + sourceCount);
    System.out.println(
        "ruptures=" + ruptureCount);
    System.out.println(
        "cascadia_interface_ruptures="
        + interfaceCount);
    System.out.println(
        "oregon_intraslab_ruptures="
        + slabCount);
    System.out.println(
        "raw_rate_sum="
        + String.format(
            Locale.US,
            "%.17g",
            rawRateSum));
    System.out.println(
        "weighted_rate_sum="
        + String.format(
            Locale.US,
            "%.17g",
            weightedRateSum));
    System.out.println(
        "output=" + outputPath);
    System.out.println(
        "finished=" + Instant.now());
  }

  private static String targetGroup(
    String treeType,
    String treePath
) {

  String path = treePath.toLowerCase(
      Locale.US);

  if (
      treeType.equals("INTERFACE")
      && path.contains("/subduction/interface/cascadia")
  ) {
    return "cascadia_interface";
  }

  if (
      treeType.equals("SLAB")
      && path.contains("/subduction/slab/or")
  ) {
    return "oregon_intraslab";
  }

  return null;
}

  private static String normalizePath(
      String value
  ) {
    return value.replace('\\', '/');
  }

  private static String integer(
      int value
  ) {
    return Integer.toString(value);
  }

  private static String number(
      double value
  ) {

    if (!Double.isFinite(value)) {
      return "";
    }

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

    boolean requiresQuotes =
        value.contains(",")
        || value.contains("\"")
        || value.contains("\n")
        || value.contains("\r");

    if (!requiresQuotes) {
      return value;
    }

    return "\""
        + value.replace(
            "\"",
            "\"\"")
        + "\"";
  }

  private static String sha256(
      String value
  ) throws Exception {

    MessageDigest digest =
        MessageDigest.getInstance(
            "SHA-256");

    byte[] bytes = digest.digest(
        value.getBytes(
            StandardCharsets.UTF_8));

    StringBuilder output =
        new StringBuilder();

    for (byte current : bytes) {
      output.append(
          String.format(
              Locale.US,
              "%02x",
              current & 0xff));
    }

    return output.toString();
  }

  private static final class SurfaceValues {

    double longitude = Double.NaN;
    double latitude = Double.NaN;
    double centroidDepth = Double.NaN;
    double topDepth = Double.NaN;
    double strike = Double.NaN;
    double dip = Double.NaN;
    double dipDirection = Double.NaN;
    double length = Double.NaN;
    double width = Double.NaN;
    double area = Double.NaN;

    static SurfaceValues from(
        RuptureSurface surface
    ) {

      SurfaceValues values =
          new SurfaceValues();

      if (surface == null) {
        return values;
      }

      try {
        Location centroid =
            surface.centroid();

        if (centroid != null) {
          values.longitude =
              centroid.longitude;

          values.latitude =
              centroid.latitude;

          values.centroidDepth =
              centroid.depth;
        }
      } catch (RuntimeException ignored) {
      }

      try {
        values.topDepth =
            surface.depth();
      } catch (RuntimeException ignored) {
      }

      try {
        values.strike =
            surface.strike();
      } catch (RuntimeException ignored) {
      }

      try {
        values.dip =
            surface.dip();
      } catch (RuntimeException ignored) {
      }

      try {
        values.dipDirection =
            surface.dipDirection();
      } catch (RuntimeException ignored) {
      }

      try {
        values.length =
            surface.length();
      } catch (RuntimeException ignored) {
      }

      try {
        values.width =
            surface.width();
      } catch (RuntimeException ignored) {
      }

      try {
        values.area =
            surface.area();
      } catch (RuntimeException ignored) {
      }

      return values;
    }
  }
}
