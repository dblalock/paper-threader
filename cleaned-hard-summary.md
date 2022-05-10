[Standing on the Shoulders of Giant Frozen Language Models](https://arxiv.org/abs/2204.10019)They
 developed techniques to get good performance on various NLP tasks
without finetuning their pretrained model at all. I’m not certain their
results are actually better than finetuning if you hold model
and inference latency constant, but they’re creative and at least work
pretty well. Their motivation is to make pretrained models more like
reusable software components, similar to the goals of T5 or [LiT](https://ai.googleblog.com/2022/04/locked-image-tuning-adding-language.html). I hope this happens, but it’s not quite clear to me yet that we can do this without a quality-speed cost.

The three approaches to using a frozen LM they consider are:

1. Input-dependent prompt tuning for multitask learning with many tasks.


![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fbucketeer-e05bbc84-baa3-437e-9518-adb32be77984.s3.amazonaws.com%2Fpublic%2Fimages%2Fae0312a3-8270-4a56-a83c-982df6f62abc_976x778.png)

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fbucketeer-e05bbc84-baa3-437e-9518-adb32be77984.s3.amazonaws.com%2Fpublic%2Fimages%2Fea913a4c-45b0-4f0c-9729-a9aab9ed3a86_982x1078.png)

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fbucketeer-e05bbc84-baa3-437e-9518-adb32be77984.s3.amazonaws.com%2Fpublic%2Fimages%2F7659cdbc-afeb-4250-84de-51730e481471_1932x944.png)

2. Training a retriever + reranking for open-domain question answering.


![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fbucketeer-e05bbc84-baa3-437e-9518-adb32be77984.s3.amazonaws.com%2Fpublic%2Fimages%2F83d04c86-a36b-4c8d-938e-57994bbae5f2_984x1226.png)

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fbucketeer-e05bbc84-baa3-437e-9518-adb32be77984.s3.amazonaws.com%2Fpublic%2Fimages%2Fd03bc1c5-7ac9-4f0a-9af1-10fda542d2b3_1934x716.png)

3. Feeding
 an LM’s output back in as input, with a learned “connector” in the
middle—evaluated for closed-book open-domain question answering. Feeding
 a model’s output back in as input isn’t new (c.f. AlphaFold, deep
equilibrium models, Universal Transformers), but using a frozen model
with a trained intermediate step is new AFAIK.


![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fbucketeer-e05bbc84-baa3-437e-9518-adb32be77984.s3.amazonaws.com%2Fpublic%2Fimages%2F15435ef2-c526-4b81-a625-3339cf85631a_1930x1040.png)

![](https://substackcdn.com/image/fetch/w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fbucketeer-e05bbc84-baa3-437e-9518-adb32be77984.s3.amazonaws.com%2Fpublic%2Fimages%2F3625b6b0-f399-44ec-ae44-aadc0e072571_2022x500.png)

This
 paper also makes me wonder how much prompt tuning and other
fine-tuning-like approaches are confounded by the size of the modules
being fine-tuned. E.g., do the proposed approaches to using a frozen LM
have especially good inductive biases, or are they just training more
parameters? Either way, I appreciate how the outside-the-box this
approach is.



