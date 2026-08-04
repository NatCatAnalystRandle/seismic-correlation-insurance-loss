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

public final class ParkerDepthInputProbe {

  private ParkerDepthInputProbe() {}

  public static void main(String[] args) throws Exception {

    if (args.length != 1) {
      throw new IllegalArgumentException(
          "Expected one output CSV path.");
    }

    Path outputPath = Path.of(args[0])
        .toAbsolutePath()
        .normalize();

    Files.createDirectories(
        outputPath.getParent());

    try (
        PrintWriter writer = new PrintWriter(
            Files.newBufferedWriter(
                outputPath,
                StandardCharsets.UTF_8))
    ) {

      writer.println(String.join(",",
          "case_id",
          "imt_name",
          "magnitude",
          "r_rup_km",
          "z_tor_km",
          "z_hyp_input_km",
          "vs30_mps",
          "branch_id",
          "branch_weight",
          "mean_ln_units",
          "median_units",
          "sigma_total_ln"
      ));

      Imt[] imts = {
          Imt.PGA,
          Imt.SA1P0
      };

      evaluate(
          writer,
          "ztor30_zhyp60",
          30.0,
          60.0,
          imts);

      evaluate(
          writer,
          "ztor50_zhyp60",
          50.0,
          60.0,
          imts);

      evaluate(
          writer,
          "ztor30_zhyp100",
          30.0,
          100.0,
          imts);
    }

    System.out.println(
        "PARKER_DEPTH_PROBE_COMPLETE");

    System.out.println(
        "output=" + outputPath);
  }

  private static void evaluate(
      PrintWriter writer,
      String caseId,
      double zTor,
      double zHyp,
      Imt[] imts
  ) {

    Gmm gmm =
        Gmm.PSBAH_20_CASCADIA_SLAB;

    double magnitude = 7.0;
    double rRup = 100.0;
    double vs30 = 760.0;

    GmmInput input = GmmInput.builder()
        .withDefaults()
        .mag(magnitude)
        .rRup(rRup)
        .zTor(zTor)
        .zHyp(zHyp)
        .vs30(vs30)
        .build();

    for (Imt imt : imts) {

      GroundMotionModel model =
          gmm.instance(imt);

      LogicTree<GroundMotion> tree =
          model.calc(input);

      for (Branch<GroundMotion> branch : tree) {

        GroundMotion motion =
            branch.value();

        writer.println(String.join(",",
            csv(caseId),
            csv(imt.name()),
            number(magnitude),
            number(rRup),
            number(zTor),
            number(zHyp),
            number(vs30),
            csv(branch.id()),
            number(branch.weight()),
            number(motion.mean()),
            number(Math.exp(motion.mean())),
            number(motion.sigma())
        ));
      }
    }
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
