import gov.usgs.earthquake.nshmp.gmm.Gmm;
import gov.usgs.earthquake.nshmp.gmm.GroundMotionModel;
import gov.usgs.earthquake.nshmp.gmm.Imt;

import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Set;

public final class ParkerGmmInventory {

  private ParkerGmmInventory() {}

  public static void main(String[] args) throws Exception {

    if (args.length != 2) {
      throw new IllegalArgumentException(
          "Expected model inventory and IMT inventory output paths.");
    }

    Path modelOutput = Path.of(args[0])
        .toAbsolutePath()
        .normalize();

    Path imtOutput = Path.of(args[1])
        .toAbsolutePath()
        .normalize();

    Files.createDirectories(
        modelOutput.getParent());

    Files.createDirectories(
        imtOutput.getParent());

    int parkerModelCount = 0;
    int parkerImtCount = 0;

    try (
        PrintWriter modelWriter = new PrintWriter(
            Files.newBufferedWriter(
                modelOutput,
                StandardCharsets.UTF_8));

        PrintWriter imtWriter = new PrintWriter(
            Files.newBufferedWriter(
                imtOutput,
                StandardCharsets.UTF_8))
    ) {

      modelWriter.println(String.join(",",
          "gmm_name",
          "gmm_label",
          "implementation_class",
          "supported_imt_count",
          "supports_pga",
          "supports_pgv",
          "constraints"
      ));

      imtWriter.println(String.join(",",
          "gmm_name",
          "gmm_label",
          "implementation_class",
          "imt_name"
      ));

      for (Gmm gmm : Gmm.values()) {

        String gmmName = gmm.name();
        String gmmLabel = gmm.toString();

        String searchText = (
            gmmName
            + " "
            + gmmLabel
        ).toLowerCase(Locale.US);

        if (!searchText.contains("parker")) {
          continue;
        }

        Set<Imt> supportedSet =
            gmm.supportedImts();

        List<Imt> supportedImts =
            new ArrayList<>(supportedSet);

        supportedImts.sort(
            Comparator.comparing(Enum::name));

        String implementationClass = "";

        if (!supportedImts.isEmpty()) {

          Imt inspectionImt =
              supportedSet.contains(Imt.PGA)
                  ? Imt.PGA
                  : supportedImts.get(0);

          GroundMotionModel model =
              gmm.instance(inspectionImt);

          implementationClass =
              model.getClass().getName();
        }

        modelWriter.println(String.join(",",
            csv(gmmName),
            csv(gmmLabel),
            csv(implementationClass),
            integer(supportedImts.size()),
            bool(supportedSet.contains(Imt.PGA)),
            bool(supportedSet.contains(Imt.PGV)),
            csv(gmm.constraints().toString())
        ));

        for (Imt imt : supportedImts) {

          imtWriter.println(String.join(",",
              csv(gmmName),
              csv(gmmLabel),
              csv(implementationClass),
              csv(imt.name())
          ));

          parkerImtCount++;
        }

        parkerModelCount++;
      }
    }

    System.out.println("PARKER_GMM_INVENTORY_COMPLETE");
    System.out.println(
        "parker_models=" + parkerModelCount);
    System.out.println(
        "parker_model_imt_pairs=" + parkerImtCount);
    System.out.println(
        "model_output=" + modelOutput);
    System.out.println(
        "imt_output=" + imtOutput);
  }

  private static String integer(int value) {
    return Integer.toString(value);
  }

  private static String bool(boolean value) {
    return Boolean.toString(value);
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
