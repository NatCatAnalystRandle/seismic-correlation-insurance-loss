import gov.usgs.earthquake.nshmp.gmm.Gmm;
import gov.usgs.earthquake.nshmp.gmm.GmmInput;
import gov.usgs.earthquake.nshmp.gmm.GroundMotion;
import gov.usgs.earthquake.nshmp.gmm.GroundMotionModel;
import gov.usgs.earthquake.nshmp.gmm.Imt;
import gov.usgs.earthquake.nshmp.tree.Branch;
import gov.usgs.earthquake.nshmp.tree.LogicTree;

import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

public final class ParkerBranchProbe {

  private ParkerBranchProbe() {}

  public static void main(String[] args) throws Exception {

    if (args.length != 3) {
      throw new IllegalArgumentException(
          "Expected interface GMM, slab GMM, and output CSV.");
    }

    String interfaceGmmName = args[0];
    String slabGmmName = args[1];

    Path outputPath = Path.of(args[2])
        .toAbsolutePath()
        .normalize();

    if (outputPath.getParent() != null) {
      Files.createDirectories(
          outputPath.getParent());
    }

    Imt[] imts = {
        Imt.PGA,
        Imt.SA0P2,
        Imt.SA1P0,
        Imt.SA2P0
    };

    int outputRows = 0;

    try (
        PrintWriter writer = new PrintWriter(
            Files.newBufferedWriter(
                outputPath,
                StandardCharsets.UTF_8))
    ) {

      writer.println(String.join(",",
          "scenario_id",
          "source_type",
          "gmm_name",
          "gmm_label",
          "implementation_class",
          "imt_name",
          "imt_period_sec",
          "magnitude",
          "r_rup_km",
          "z_hyp_km",
          "vs30_mps",
          "logic_tree_name",
          "branch_index",
          "branch_id",
          "branch_weight",
          "mean_ln_units",
          "median_units",
          "sigma_total_ln"
      ));

      outputRows += evaluateScenario(
          writer,
          "interface_m9_reference_rock",
          "interface",
          interfaceGmmName,
          9.0,
          100.0,
          20.0,
          760.0,
          imts);

      outputRows += evaluateScenario(
          writer,
          "slab_m7_reference_rock",
          "intraslab",
          slabGmmName,
          7.0,
          100.0,
          60.0,
          760.0,
          imts);
    }

    System.out.println(
        "PARKER_BRANCH_PROBE_COMPLETE");

    System.out.println(
        "output_rows=" + outputRows);

    System.out.println(
        "output=" + outputPath);
  }

  private static int evaluateScenario(
      PrintWriter writer,
      String scenarioId,
      String sourceType,
      String gmmName,
      double magnitude,
      double rRup,
      double zHyp,
      double vs30,
      Imt[] imts
  ) {

    Gmm gmm = Gmm.valueOf(
        gmmName);

    GmmInput input = GmmInput.builder()
        .withDefaults()
        .mag(magnitude)
        .rRup(rRup)
        .zHyp(zHyp)
        .vs30(vs30)
        .build();

    int rowCount = 0;

    for (Imt imt : imts) {

      GroundMotionModel model =
          gmm.instance(imt);

      LogicTree<GroundMotion> tree =
          model.calc(input);

      for (
          int branchIndex = 0;
          branchIndex < tree.size();
          branchIndex++
      ) {

        Branch<GroundMotion> branch =
            tree.get(branchIndex);

        GroundMotion motion =
            branch.value();

        double mean =
            motion.mean();

        double sigma =
            motion.sigma();

        double median =
            Math.exp(mean);

        writer.println(String.join(",",
            csv(scenarioId),
            csv(sourceType),
            csv(gmm.name()),
            csv(gmm.toString()),
            csv(model.getClass().getName()),
            csv(imt.name()),
            number(
                imt.isSA()
                    ? imt.period()
                    : Double.NaN),
            number(magnitude),
            number(rRup),
            number(zHyp),
            number(vs30),
            csv(tree.name()),
            integer(branchIndex),
            csv(branch.id()),
            number(branch.weight()),
            number(mean),
            number(median),
            number(sigma)
        ));

        rowCount++;
      }
    }

    return rowCount;
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
