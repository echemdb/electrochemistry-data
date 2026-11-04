**Fixed:**

* Fixed invalid ``geometricElectrolyteContactArea`` of the working electrode in 43 entries (#181). The key is removed where the publication does not report an area; the electrode diameter from the publication is recorded in ``shape.diameter`` instead (``briega-martos_2020_hydrogen_135452``, ``briega-martos_2021_cation_48``, ``chen_2024_deconvolution_4958``, ``cuesta_2000_adsorption_5684``, ``engstfeld_2018_polycrystalline_17743``, ``sato_2006_effect_725``).
* Fixed the working electrode area of ``jerkiewicz_2009_effect_12309`` (``0.0431 cm2`` instead of ``4.31 1 / mm2``) and the electrode diameter, using the values and uncertainties reported in the publication.
* Fixed the electrode diameter of ``engstfeld_2018_polycrystalline_17743`` (6 mm sample in the hanging meniscus cell, 8 mm sample in the flow cell) and described how the electrolyte contact area is defined in each cell.
* Fixed ``durand_1992_situ_1977``: added the working electrode area (``1.12 cm2``) and dimensions, corrected the crystallographic orientation (``100`` instead of ``110``), the reference electrode (SCE instead of RHE), and the swapped value and unit of the Ar pressure.
* Fixed empty ``shape.height`` entries without a value in ``briega-martos_2020_hydrogen_135452``, ``briega-martos_2021_cation_48`` and ``chen_2024_deconvolution_4958``.
