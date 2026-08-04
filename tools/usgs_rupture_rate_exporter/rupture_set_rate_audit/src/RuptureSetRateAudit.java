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
import java.util.Locale;

public final class RuptureSetRateAudit {

  private RuptureSetRateAudit() {}

  public static void main(String[] args) throws Exception {

    if (args.length != 2) {
      throw new IllegalArgumentException(
          "Expected a model directory and output CSV.");
    }

    Path modelPath =
        Path.of(args[0]).toAbsolutePath().normalize();

    Path outputPath =
        Path.of(args[1]).toAbsolutePath().normalize();

    HazardModel model =
        HazardModel.load(modelPath);

    if (outputPath.getParent() != null) {
      Files.createDirectories(
          outputPath.getParent());
    }

    long selectedSetCount = 0;
    long selectedRuptureCount = 0;

    try (
        PrintWriter writer = new PrintWriter(
            Files.newBufferedWriter(
                outputPath,
                StandardCharsets.UTF_8))
    ) {

      writer.println(String.join(",",
          "target_group",
          "tree_id",
          "tree_name",
          "tree_path",
          "tree_type",
          "branch_index",
          "branch_weight",
          "rupture_set_id",
          "rupture_set_name",
          "rupture_set_type",
          "rupture_set_weight",
          "source_count",
          "rupture_count",
          "iterated_raw_rate_sum",
          "total_mfd_rate_sum",
          "iterated_weighted_rate_sum",
          "weighted_total_mfd_rate_sum"
      ));

      for (SourceTree tree : model) {

        String treePath =
            tree.path().toString().replace('\\', '/');

        String targetGroup =
            targetGroup(
                tree.type().name(),
                treePath);

        if (targetGroup == null) {
          continue;
        }

        for (
            int branchIndex = 0;
            branchIndex < tree.size();
            branchIndex++
        ) {

          Branch<RuptureSet<? extends Source>> branch =
              tree.get(branchIndex);

          RuptureSet<? extends Source> ruptureSet =
              branch.value();

          long ruptureCount = 0;
          double iteratedRawRate = 0.0;

          for (
              int sourceIndex = 0;
              sourceIndex < ruptureSet.size();
              sourceIndex++
          ) {

            Source source =
                ruptureSet.get(sourceIndex);

            for (
                int ruptureIndex = 0;
                ruptureIndex < source.size();
                ruptureIndex++
            ) {

              Rupture rupture =
                  source.get(ruptureIndex);

              iteratedRawRate +=
                  rupture.rate();

              ruptureCount++;
            }
          }

          double totalMfdRate =
              ruptureSet
                  .totalMfd()
                  .data()
                  .yValues()
                  .sum();

          double setWeight =
              ruptureSet.weight();

          writer.println(String.join(",",
              csv(targetGroup),
              integer(tree.id()),
              csv(tree.name()),
              csv(treePath),
              csv(tree.type().name()),
              integer(branchIndex),
              number(branch.weight()),
              integer(ruptureSet.id()),
              csv(ruptureSet.name()),
              csv(ruptureSet.type().name()),
              number(setWeight),
              integer(ruptureSet.size()),
              number(ruptureCount),
              number(iteratedRawRate),
              number(totalMfdRate),
              number(iteratedRawRate * setWeight),
              number(totalMfdRate * setWeight)
          ));

          selectedSetCount++;
          selectedRuptureCount += ruptureCount;
        }
      }
    }

    System.out.println("AUDIT_COMPLETE");
    System.out.println(
        "rupture_sets=" + selectedSetCount);
    System.out.println(
        "ruptures=" + selectedRuptureCount);
    System.out.println(
        "output=" + outputPath);
  }

  private static String targetGroup(
      String treeType,
      String treePath
  ) {

    String path =
        treePath.toLowerCase(Locale.US);

    if (
        treeType.equals("INTERFACE")
        && path.contains(
            "/subduction/interface/cascadia")
    ) {
      return "cascadia_interface";
    }

    if (
        treeType.equals("SLAB")
        && path.contains(
            "/subduction/slab/or")
    ) {
      return "oregon_intraslab";
    }

    return null;
  }

  private static String integer(
      long value
  ) {
    return Long.toString(value);
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
