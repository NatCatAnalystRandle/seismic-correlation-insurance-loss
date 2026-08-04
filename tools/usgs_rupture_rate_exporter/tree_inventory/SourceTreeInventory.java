import gov.usgs.earthquake.nshmp.model.HazardModel;
import gov.usgs.earthquake.nshmp.model.RuptureSet;
import gov.usgs.earthquake.nshmp.model.Source;
import gov.usgs.earthquake.nshmp.model.SourceTree;
import gov.usgs.earthquake.nshmp.tree.Branch;

import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

public final class SourceTreeInventory {

  private SourceTreeInventory() {}

  public static void main(String[] args) throws Exception {

    if (args.length != 2) {
      throw new IllegalArgumentException(
          "Expected model directory and output CSV.");
    }

    Path modelPath = Path.of(args[0]);
    Path outputPath = Path.of(args[1]);

    HazardModel model = HazardModel.load(modelPath);

    if (outputPath.getParent() != null) {
      Files.createDirectories(outputPath.getParent());
    }

    try (
        PrintWriter writer = new PrintWriter(
            Files.newBufferedWriter(
                outputPath,
                StandardCharsets.UTF_8))
    ) {

      writer.println(String.join(",",
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
          "source_count"
      ));

      for (SourceTree tree : model) {

        String treeType = tree.type().name();

        if (
            !treeType.contains("INTERFACE")
            && !treeType.contains("SLAB")
        ) {
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

          writer.println(String.join(",",
              integer(tree.id()),
              csv(tree.name()),
              csv(tree.path().toString().replace('\\', '/')),
              csv(treeType),
              csv(tree.setting().name()),
              integer(branchIndex),
              number(branch.weight()),
              integer(ruptureSet.id()),
              csv(ruptureSet.name()),
              csv(ruptureSet.type().name()),
              number(ruptureSet.weight()),
              integer(ruptureSet.size())
          ));
        }
      }
    }

    System.out.println("INVENTORY_COMPLETE");
    System.out.println("output=" + outputPath);
  }

  private static String integer(int value) {
    return Integer.toString(value);
  }

  private static String number(double value) {
    return String.format(
        Locale.US,
        "%.17g",
        value);
  }

  private static String csv(String value) {

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
